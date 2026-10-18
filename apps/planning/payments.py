from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import RegistrationPayment


def ensure_payment(application):
    """Idempotent payment record creation after definitive placement."""
    if not application.linked_enrollment_id:
        raise ValueError('Only finalized applications can have payment obligations')
    payment, _ = RegistrationPayment.objects.get_or_create(
        application=application,
        defaults={
            'reference': f'MHAV-{application.pk:06d}',
            'due_at': timezone.now() + timedelta(days=14),
        },
    )
    return payment
