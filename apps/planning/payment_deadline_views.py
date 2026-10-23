from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core import signing
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from .models import CourseApplication, RegistrationPayment, RegistrationPaymentEvent
from .views import is_planner
from .payment_lifecycle import withdrawal_signer, cancel_unpaid
from .payment_emails import payment_received_body
from .notifications import notify_after_commit
from .stripe_views import guest_payment_signer
from django.urls import reverse

@require_http_methods(['GET', 'POST'])
def decline(request, token):
    try:
        pk = int(withdrawal_signer().unsign(token, max_age=30*86400))
    except (signing.BadSignature, signing.SignatureExpired, ValueError):
        return HttpResponseBadRequest('Deze link is ongeldig of verlopen. Neem contact op met MHAV.')
    application = get_object_or_404(CourseApplication, pk=pk)
    payment = getattr(application, 'payment', None)
    available = bool(payment and payment.status == 'pending' and not payment.cancelled_at and application.status == 'processed' and application.linked_enrollment_id)
    if request.method == 'POST':
        if not available:
            return HttpResponseBadRequest('Deze inschrijving kan niet via deze link worden geannuleerd.')
        if cancel_unpaid(pk, 'participant'):
            return render(request, 'planning/payment_decline.html', {'done': True})
        return HttpResponseBadRequest('Annuleren is niet mogelijk. Neem contact op met MHAV.')
    return render(request, 'planning/payment_decline.html', {'application': application, 'available': available})

@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def manage(request, pk):
    action = request.POST.get('action')
    note = request.POST.get('note', '').strip()
    if not note:
        messages.error(request, 'Een toelichting is verplicht.')
        return redirect('planning:application_detail', pk=pk)
    with transaction.atomic():
        application = get_object_or_404(CourseApplication.objects.select_for_update(), pk=pk)
        payment = get_object_or_404(RegistrationPayment.objects.select_for_update(), application=application)
        if payment.status != 'pending' or payment.cancelled_at or application.status != 'processed':
            messages.error(request, 'De betalingsverplichting is niet meer actief.')
            return redirect('planning:application_detail', pk=pk)
        if action == 'deadline':
            from datetime import datetime
            from django.utils.dateparse import parse_date
            date = parse_date(request.POST.get('due_date', ''))
            if not date or date < timezone.localdate():
                messages.error(request, 'Kies een geldige toekomstige betaaldatum.')
                return redirect('planning:application_detail', pk=pk)
            payment.due_at = timezone.make_aware(datetime.combine(date, datetime.min.time().replace(hour=23, minute=59)))
            payment.reminder_sent_at = None
            payment.grace_notice_sent_at = None
            payment.save(update_fields=['due_at', 'reminder_sent_at', 'grace_notice_sent_at', 'updated_at'])
            RegistrationPaymentEvent.objects.create(payment=payment, action='deadline_changed', actor=request.user, note=note)
            from django.urls import reverse
            token = guest_payment_signer().sign(str(application.pk))
            pay_url = request.build_absolute_uri(reverse('planning:stripe_guest_checkout', args=[token]))
            notify_after_commit('MHAV - Nieuwe betaaldatum cursus',
                f'Beste {application.first_name},\n\nDe betaaldatum voor {application.course} '
                f'(lesgroep: {application.linked_enrollment.group.name}) is gewijzigd.\n'
                f'Nieuwe betaaldatum: {payment.due_at:%d-%m-%Y}.\n'
                f'Openstaand bedrag: € {payment.amount_due:.2f}.\n\n'
                f'Betaal veilig via: {pay_url}\n\n'
                'Heb je al betaald? Neem dan contact op met MHAV.\n\nMijn Hond Als Vriend',
                [application.email])
            messages.success(request, 'Betaaltermijn bijgewerkt. Cursist ontvangt een e-mail.')
        elif action == 'resend':
            if not payment.amount_due:
                messages.error(request, 'Stel eerst het cursusbedrag vast.')
                return redirect('planning:application_detail', pk=pk)
            token = guest_payment_signer().sign(str(application.pk))
            pay_url = request.build_absolute_uri(reverse('planning:stripe_guest_checkout', args=[token]))
            notify_after_commit('MHAV - Betalingsverzoek cursus',
                f'Beste {application.first_name},\n\nVoor {application.course} staat nog € {payment.amount_due:.2f} open.\n'
                f'Lesgroep: {application.linked_enrollment.group.name}\nBetaal vóór: {payment.due_at:%d-%m-%Y}\n\n'
                f'Betaallink (14 dagen geldig): {pay_url}\n'
                f'Cursusplaats afwijzen: {request.build_absolute_uri(reverse("planning:payment_decline", args=[__import__("apps.planning.payment_lifecycle", fromlist=["withdrawal_signer"]).withdrawal_signer().sign(str(application.pk))]))}\n\nMijn Hond Als Vriend', [application.email])
            RegistrationPaymentEvent.objects.create(payment=payment, action='request_resent', actor=request.user, note=note)
            messages.success(request, 'Betalingsverzoek opnieuw verzonden.')
        else:
            messages.error(request, 'Onbekende actie.')
    return redirect('planning:application_detail', pk=pk)
