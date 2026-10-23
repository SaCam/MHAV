"""Administrator-initiated cancellation of a definitive course placement."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import (
    CourseApplication,
    Enrollment,
    RegistrationPayment,
    RegistrationPaymentEvent,
    StripeCheckoutAttempt,
)
from .notifications import notify_after_commit
from .views import is_planner


@require_http_methods(['GET', 'POST'])
@user_passes_test(is_planner, login_url='accounts:login')
def cancel_placement(request, pk):
    """Keep payment and enrollment history; only release an active place."""
    application = get_object_or_404(
        CourseApplication.objects.select_related(
            'course', 'linked_enrollment__group__season'
        ),
        pk=pk,
    )
    enrollment = application.linked_enrollment
    payment = RegistrationPayment.objects.filter(application=application).first()

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        note = request.POST.get('note', '').strip()
        confirmed = request.POST.get('confirm') == 'yes'
        if reason not in ('nonpayment', 'participant', 'administrative') or not note or not confirmed:
            messages.error(request, 'Kies een reden, geef een toelichting en bevestig de annulering.')
            return redirect('planning:admin_cancel_placement', pk=pk)

        with transaction.atomic():
            application = CourseApplication.objects.select_for_update().get(pk=pk)
            payment = RegistrationPayment.objects.select_for_update().filter(
                application=application
            ).first()
            if not application.linked_enrollment_id:
                messages.error(request, 'Er is geen definitieve inschrijving.')
                return redirect('planning:application_detail', pk=pk)

            enrollment = Enrollment.objects.select_for_update().get(
                pk=application.linked_enrollment_id
            )
            group = enrollment.group
            if enrollment.status != Enrollment.Status.PLACED or application.status != CourseApplication.Status.PROCESSED:
                messages.error(request, 'Deze inschrijving is niet meer actief.')
                return redirect('planning:application_detail', pk=pk)
            if group.execution_status != 'planned':
                messages.error(request, 'Een gestarte of afgesloten lesgroep kan hier niet worden geannuleerd.')
                return redirect('planning:application_detail', pk=pk)
            if reason == 'nonpayment' and payment and payment.status != RegistrationPayment.Status.PENDING:
                messages.error(request, 'Annuleren wegens wanbetaling is alleen mogelijk bij een openstaande betaling.')
                return redirect('planning:admin_cancel_placement', pk=pk)

            recent_checkout = bool(payment and StripeCheckoutAttempt.objects.filter(
                payment=payment,
                created_at__gte=timezone.now() - timedelta(hours=48),
            ).exists())
            if recent_checkout and payment.status == RegistrationPayment.Status.PENDING:
                messages.error(
                    request,
                    'Er is recent een Stripe-betaalpoging gestart. Controleer de betaling eerst '
                    'in Stripe en wacht tot de betaling definitief is verwerkt.',
                )
                return redirect('planning:admin_cancel_placement', pk=pk)

            enrollment.status = Enrollment.Status.CANCELLED
            enrollment.notes = '\n'.join(filter(None, [enrollment.notes, f'Annulering door beheerder ({reason}): {note}']))
            enrollment.save(update_fields=['status', 'notes'])

            application.status = CourseApplication.Status.REJECTED
            application.closure_reason = 'withdrawn' if reason == 'participant' else 'other'
            application.closure_note = note
            application.handled_at = timezone.now()
            application.handled_by = request.user
            application.save(update_fields=[
                'status', 'closure_reason', 'closure_note',
                'handled_at', 'handled_by', 'updated_at',
            ])

            if payment:
                payment.cancelled_at = timezone.now()
                payment.cancellation_reason = reason
                payment.save(update_fields=[
                    'cancelled_at', 'cancellation_reason', 'updated_at'
                ])
                RegistrationPaymentEvent.objects.create(
                    payment=payment,
                    action='cancelled',
                    actor=request.user,
                    note=f'Handmatig geannuleerd ({reason}): {note}',
                    old_status=payment.status,
                    new_status=payment.status,
                )

            refund_note = (
                '\nEen eventuele terugbetaling wordt afzonderlijk beoordeeld.'
                if payment and payment.status == RegistrationPayment.Status.PAID
                else ''
            )
            notify_after_commit(
                'MHAV - Cursusinschrijving geannuleerd',
                (
                    f'Beste {application.first_name},\n\n'
                    f'Je inschrijving voor {application.course} in lesgroep '
                    f'{group.name} is geannuleerd. De lesplaats is vrijgegeven.'
                    f'{refund_note}\n\nMijn Hond Als Vriend'
                ),
                [application.email],
            )
            messages.success(request, 'Inschrijving geannuleerd. De lesplaats is vrijgegeven.')
            return redirect('planning:group_detail', pk=group.pk)

    return render(request, 'planning/admin_cancel_placement.html', {
        'application': application,
        'enrollment': enrollment,
        'payment': payment,
        'can_cancel': bool(
            enrollment and enrollment.status == Enrollment.Status.PLACED
            and application.status == CourseApplication.Status.PROCESSED
            and enrollment.group.execution_status == 'planned'
        ),
    })
