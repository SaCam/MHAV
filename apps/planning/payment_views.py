from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import CourseApplication, RegistrationPayment, RegistrationPaymentEvent
from .views import is_planner
from .payments import ensure_payment
from .notifications import notify_after_commit
from .payment_emails import payment_received_body


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def payment_action(request, pk):
    action = request.POST.get('action')
    note = request.POST.get('note', '').strip()
    if not note:
        messages.error(request, 'Een toelichting is verplicht voor iedere betalingswijziging.')
        return redirect('planning:application_detail', pk=pk)
    with transaction.atomic():
        application = get_object_or_404(CourseApplication.objects.select_for_update(), pk=pk)
        if not application.linked_enrollment_id or application.status != CourseApplication.Status.PROCESSED:
            messages.error(request, 'Betaling kan pas na definitieve plaatsing worden beheerd.')
            return redirect('planning:application_detail', pk=pk)
        payment = ensure_payment(application)
        payment = RegistrationPayment.objects.select_for_update().get(pk=payment.pk)
        if action == 'initialize':
            RegistrationPaymentEvent.objects.create(payment=payment, action='initialized',
                actor=request.user, note=note, old_status=payment.status, new_status=payment.status)
            messages.success(request, 'Betalingsregistratie beschikbaar.')
            return redirect('planning:application_detail', pk=pk)
        if payment.status != RegistrationPayment.Status.PENDING:
            messages.error(request, 'Deze betaling is al afgehandeld en kan niet opnieuw worden verwerkt.')
            return redirect('planning:application_detail', pk=pk)
        old = payment.status
        if action == 'amount':
            try:
                amount = Decimal(request.POST.get('amount', ''))
                if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2 or amount > Decimal('9999999.99'):
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, 'Vul een geldig cursusbedrag groter dan nul in (maximaal twee decimalen).')
                return redirect('planning:application_detail', pk=pk)
            previous_amount = payment.amount_due
            payment.amount_due = amount
            payment.save(update_fields=['amount_due', 'updated_at'])
            event = 'amount_set'
            if previous_amount != amount:
                from django.urls import reverse
                from .stripe_views import guest_payment_signer
                token = guest_payment_signer().sign(str(application.pk))
                pay_url = request.build_absolute_uri(reverse('planning:stripe_guest_checkout', args=[token]))
                group = application.linked_enrollment.group
                notify_after_commit('MHAV - Betalingsverzoek cursus',
                    f'Beste {application.first_name},\n\nJe bent definitief ingeschreven voor {application.course.title}.\n'
                    f'Lesgroep: {group.name}\nCursusbedrag: € {amount:.2f}\n'
                    f'Betaal vóór: {payment.due_at:%d-%m-%Y}\n\n'
                    f'Betaal veilig via deze persoonlijke link (14 dagen geldig):\n{pay_url}\n\n'
                    'Heb je al betaald? Neem dan contact op met MHAV.\n\nMijn Hond Als Vriend',
                    [application.email])
        elif action == 'paid':
            if not payment.amount_due or payment.amount_due <= 0:
                messages.error(request, 'Stel eerst het cursusbedrag vast.')
                return redirect('planning:application_detail', pk=pk)
            method = request.POST.get('method')
            if method not in ('bank', 'cash', 'other'):
                messages.error(request, 'Kies een geldige betaalmethode.')
                return redirect('planning:application_detail', pk=pk)
            from django.utils import timezone
            payment.status = RegistrationPayment.Status.PAID
            payment.method = method
            payment.paid_at = timezone.now()
            payment.paid_by = request.user
            payment.note = note
            payment.save(update_fields=['status','method','paid_at','paid_by','note','updated_at'])
            event = 'marked_paid'
            notify_after_commit('MHAV - Betaling ontvangen',
                payment_received_body(payment),
                [application.email])
        else:
            messages.error(request, 'Onbekende betalingsactie.')
            return redirect('planning:application_detail', pk=pk)
        RegistrationPaymentEvent.objects.create(payment=payment, action=event,
            actor=request.user, note=note, old_status=old, new_status=payment.status)
    messages.success(request, 'Betalingsgegevens opgeslagen. De wijziging is geregistreerd.')
    return redirect('planning:application_detail', pk=pk)
