"""Local-only, opt-in cleanup of MHAV registration and season test data."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.models import Q

from apps.planning.models import (
    Combination, CourseApplication, Dog, Enrollment, LessonInstructorOverride,
    LessonRecord, RegistrationPayment, RegistrationPaymentEvent, Season,
    SeasonCourseOffering, StripeCheckoutAttempt, TrainerSeasonAvailability,
    TrainingGroup,
)


class Command(BaseCommand):
    help = 'Preview or reset LOCAL MHAV test registrations, participants and seasons; preserve course definitions and staff.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Actually delete data (default: preview only).')
        parser.add_argument('--confirm-db', default='', help='Type the exact database name as a second confirmation.')

    def handle(self, *args, **options):
        db = connections['default']
        cfg = db.settings_dict
        db_name = str(cfg.get('NAME') or '')
        host = str(cfg.get('HOST') or '').strip().lower()
        if not settings.DEBUG:
            raise CommandError('Refusing to run: DJANGO_DEBUG must be True.')
        if db.vendor != 'postgresql' or host not in ('localhost', '127.0.0.1', '::1'):
            raise CommandError('Refusing to run: this command only supports PostgreSQL on localhost.')
        if not db_name:
            raise CommandError('Database name is missing.')
        # Explicitly reject common production database names even if tunnelled to localhost.
        if any(part in db_name.lower() for part in ('prod', 'production', 'live')):
            raise CommandError('Database name resembles production; refusing to run.')

        User = get_user_model()
        participants = User.objects.exclude(Q(is_staff=True) | Q(is_superuser=True))
        targets = [
            ('Stripe checkout attempts', StripeCheckoutAttempt.objects.all()),
            ('Payment audit events', RegistrationPaymentEvent.objects.all()),
            ('Payments', RegistrationPayment.objects.all()),
            ('Applications', CourseApplication.objects.all()),
            ('Lesson records', LessonRecord.objects.all()),
            ('Enrollments', Enrollment.objects.all()),
            ('Instructor substitutions', LessonInstructorOverride.objects.all()),
            ('Groups', TrainingGroup.objects.all()),
            ('Season course offerings', SeasonCourseOffering.objects.all()),
            ('Trainer availability', TrainerSeasonAvailability.objects.all()),
            ('Seasons', Season.objects.all()),
            ('Handler/dog combinations', Combination.objects.all()),
            ('Dogs', Dog.objects.all()),
            ('Non-staff user accounts', participants),
        ]
        self.stdout.write(self.style.WARNING(f'LOCAL TEST DATA RESET — database: {db_name} @ {host}'))
        self.stdout.write('Preserved: staff/superuser accounts, website course definitions, website content, role groups, migrations.')
        self.stdout.write('WARNING: all seasons, ALL applications/payments and ALL dogs/combinations will be deleted.')
        for label, qs in targets:
            self.stdout.write(f'  {label}: {qs.count()}')
        self.stdout.write(f'  Active sessions (all users): {Session.objects.count()}')

        if not options['apply']:
            self.stdout.write(self.style.SUCCESS('DRY RUN ONLY — no records deleted.'))
            self.stdout.write(f'To apply: python manage.py reset_test_data --apply --confirm-db "{db_name}"')
            return
        if options['confirm_db'] != db_name:
            raise CommandError('Confirmation failed. Pass --confirm-db with the exact database name shown above.')

        # Deletion order matters: payments and their protected audit/session records
        # precede applications; enrollments precede groups; groups precede seasons.
        with transaction.atomic():
            for label, qs in targets:
                count = qs.count()
                qs.delete()
                self.stdout.write(f'Deleted {label}: {count}')
            Session.objects.all().delete()  # Clear old logins; administrator logs in again.
        self.stdout.write(self.style.SUCCESS('Local test data reset completed. Staff and course definitions preserved.'))
