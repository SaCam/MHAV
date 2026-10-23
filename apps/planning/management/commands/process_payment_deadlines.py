"""Run daily via cron/systemd timer. Dry-run by default; --apply sends emails and cancels."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.planning.models import RegistrationPayment, RegistrationPaymentEvent, StripeCheckoutAttempt, SeasonCourseOffering
from apps.planning.payment_lifecycle import cancel_unpaid, withdrawal_signer
from apps.planning.notifications import notify_after_commit
from django.urls import reverse
from django.conf import settings

class Command(BaseCommand):
    help = 'Review payment deadlines. Dry-run unless --apply is provided.'
    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--grace-days', type=int, default=3)
        parser.add_argument('--remind-days', type=int, default=7)
    def handle(self, *args, **options):
        if options['grace_days'] < 0 or options['remind_days'] < 1:
            raise ValueError('Grace and reminder days must be positive')
        now = timezone.now()
        origin = getattr(settings, 'MHAV_PUBLIC_BASE_URL', '').rstrip('/')
        if options['apply'] and not origin:
            raise ValueError('Configure MHAV_PUBLIC_BASE_URL before running --apply')
        for pk in RegistrationPayment.objects.filter(status='pending', cancelled_at__isnull=True, amount_due__gt=0, due_at__isnull=False).values_list('pk', flat=True):
            with transaction.atomic():
                payment = RegistrationPayment.objects.select_for_update(of=('self',)).select_related('application__course').get(pk=pk)
                app = payment.application
                if app.status != 'processed' or not app.linked_enrollment_id:
                    continue
                group = app.linked_enrollment.group
                offering = SeasonCourseOffering.objects.filter(season=group.season, course=app.course).first()
                grace_days = offering.grace_period_days if offering else options['grace_days']
                reminder_days = min(options['remind_days'], max(1, (offering.payment_term_days // 2) if offering else options['remind_days']))
                age = now - payment.due_at
                if age >= timedelta(days=grace_days):
                    if StripeCheckoutAttempt.objects.filter(payment=payment, created_at__gte=now-timedelta(hours=48)).exists():
                        self.stdout.write(f'PAYMENT {pk}: recent Stripe attempt, manual reconciliation needed')
                        continue
                    self.stdout.write(f'PAYMENT {pk}: cancellation eligible')
                    if options['apply']:
                        cancel_unpaid(app.pk, 'deadline')
                elif age >= timedelta(0) and not payment.grace_notice_sent_at:
                    self.stdout.write(f'PAYMENT {pk}: grace notice')
                    if options['apply']:
                        notify_after_commit('MHAV - Betalingstermijn verstreken', f'Beste {app.first_name},\n\nDe betaling voor {app.course} is nog niet ontvangen. Betaal binnen {grace_days} dagen of neem contact op met MHAV om annulering te voorkomen.\n\nMijn Hond Als Vriend', [app.email])
                        payment.grace_notice_sent_at=now
                        payment.save(update_fields=['grace_notice_sent_at','updated_at'])
                        RegistrationPaymentEvent.objects.create(payment=payment, action='grace_notice', note='Automatische waarschuwing na betaaldatum')
                elif payment.due_at - now <= timedelta(days=reminder_days) and age < timedelta(0) and not payment.reminder_sent_at:
                    self.stdout.write(f'PAYMENT {pk}: reminder')
                    if options['apply']:
                        from apps.planning.stripe_views import guest_payment_signer
                        token=guest_payment_signer().sign(str(app.pk))
                        pay_url=origin+reverse('planning:stripe_guest_checkout', args=[token])
                        notify_after_commit('MHAV - Herinnering cursusbetaling', f'Beste {app.first_name},\n\nVoor {app.course} staat € {payment.amount_due:.2f} open. Betaal vóór {payment.due_at:%d-%m-%Y}.\n\nBetaallink: {pay_url}\n\nMijn Hond Als Vriend', [app.email])
                        payment.reminder_sent_at=now
                        payment.save(update_fields=['reminder_sent_at','updated_at'])
                        RegistrationPaymentEvent.objects.create(payment=payment, action='reminder', note='Automatische betalingsherinnering')
