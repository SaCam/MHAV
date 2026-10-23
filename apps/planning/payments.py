from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import RegistrationPayment, SeasonCourseOffering


def ensure_payment(application):
    """Idempotent payment record creation after definitive placement."""
    if not application.linked_enrollment_id:
        raise ValueError('Only finalized applications can have payment obligations')
    enrollment = application.linked_enrollment
    offering = SeasonCourseOffering.objects.filter(season=enrollment.group.season, course=application.course).first()
    defaults = {'reference': f'MHAV-{application.pk:06d}',
                'due_at': timezone.now() + timedelta(days=offering.payment_term_days if offering else 14)}
    if offering and offering.course_price is not None:
        defaults['amount_due'] = offering.course_price
    payment, _ = RegistrationPayment.objects.get_or_create(
        application=application,
        defaults=defaults,
    )
    return payment


def payment_price_problem(application, group):
    """Fail closed when the season/course price was not configured."""
    offering = SeasonCourseOffering.objects.filter(
        season=group.season,
        course=application.course,
    ).first()
    if offering is None or offering.course_price is None or offering.course_price <= 0:
        return (
            f'Geen cursusprijs ingesteld voor {application.course.title} '
            f'in {group.season}. Stel eerst de prijs in bij Financiën.'
        )
    return None


def send_payment_request(request, application, group, payment):
    """Queue a payment invitation after the enrollment transaction commits."""
    if payment.amount_due is None or payment.amount_due <= 0:
        return
    from django.urls import reverse
    from .stripe_views import guest_payment_signer
    from .notifications import notify_after_commit

    token = guest_payment_signer().sign(str(application.pk))
    pay_url = request.build_absolute_uri(
        reverse('planning:stripe_guest_checkout', args=[token])
    )
    notify_after_commit(
        'MHAV - Betalingsverzoek cursus',
        f'Beste {application.first_name},\n\n'
        f'Je bent definitief geplaatst in {group.name}.\n'
        f'Cursus: {application.course.title}\n'
        f'Bedrag: € {payment.amount_due:.2f}\n'
        f'Betaal vóór: {payment.due_at:%d-%m-%Y}\n\n'
        f'Betaal via deze persoonlijke link:\n{pay_url}\n\n'
        'Mijn Hond Als Vriend',
        [application.email],
    )
