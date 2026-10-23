"""Deadline and withdrawal lifecycle. Never delete enrollment/payment history."""
from datetime import timedelta
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from .models import CourseApplication, Enrollment, RegistrationPayment, RegistrationPaymentEvent, StripeCheckoutAttempt
from .notifications import notify_after_commit


def withdrawal_signer():
    return signing.TimestampSigner(salt='mhav-withdrawal-v1')


def withdrawal_url(request, application):
    return request.build_absolute_uri(reverse('planning:payment_decline', args=[withdrawal_signer().sign(str(application.pk))]))


def cancel_unpaid(application_id, reason, actor=None):
    """Return True only if cancellation completed; row locks serialize with Stripe webhook."""
    with transaction.atomic():
        application = CourseApplication.objects.select_for_update().get(pk=application_id)
        payment = RegistrationPayment.objects.select_for_update().filter(application=application).first()
        if not payment or payment.status != RegistrationPayment.Status.PENDING or payment.cancelled_at:
            return False
        if application.status != CourseApplication.Status.PROCESSED or not application.linked_enrollment_id:
            return False
        enrollment = Enrollment.objects.select_for_update().get(pk=application.linked_enrollment_id)
        if enrollment.status != Enrollment.Status.PLACED:
            return False
        # A Stripe session may still settle asynchronously. Do not automatically cancel
        # if checkout was initiated recently; require manual reconciliation instead.
        if reason == 'deadline' and StripeCheckoutAttempt.objects.filter(
            payment=payment, created_at__gte=timezone.now() - timedelta(hours=48)
        ).exists():
            return False
        now = timezone.now()
        enrollment.status = Enrollment.Status.CANCELLED
        enrollment.save(update_fields=['status'])
        application.status = CourseApplication.Status.REJECTED
        application.closure_reason = 'withdrawn'
        application.save(update_fields=['status', 'closure_reason', 'updated_at'])
        payment.cancelled_at = now
        payment.cancellation_reason = reason
        payment.save(update_fields=['cancelled_at', 'cancellation_reason', 'updated_at'])
        RegistrationPaymentEvent.objects.create(payment=payment, action='cancelled', actor=actor,
            note='Cursist heeft plaats afgewezen' if reason == 'participant' else 'Betalingstermijn en respijtperiode verstreken',
            old_status='pending', new_status='pending')
        notify_after_commit('MHAV - Cursusinschrijving geannuleerd',
            f'Beste {application.first_name},\n\nJe inschrijving voor {application.course} is geannuleerd. '
            'De gereserveerde lesplaats is vrijgegeven. Wil je alsnog deelnemen, dien dan een nieuwe aanmelding in.\n\nMijn Hond Als Vriend',
            [application.email])
        return True
