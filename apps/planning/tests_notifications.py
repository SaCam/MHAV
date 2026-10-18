from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from .models import CourseApplication
from .notifications import participant_confirmed, participant_declined, placement_confirmed, application_closed

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   MHAV_REGISTRATION_NOTIFICATION_EMAIL='beheer@example.org')
class NotificationTests(TestCase):
    def setUp(self):
        self.app = CourseApplication.objects.create(first_name='Test', last_name='Cursist',
            email='cursist@example.org', dog_name='Bello', privacy_accepted_at=timezone.now())

    def test_confirmed_application_notifies_participant_and_admin_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            participant_confirmed(self.app)
        self.assertEqual(len(callbacks), 2)
        self.assertEqual({m.to[0] for m in mail.outbox}, {'cursist@example.org','beheer@example.org'})
        self.assertIn('nog geen definitieve cursusplaats', mail.outbox[0].body)

    def test_decline_notifies_admin_only(self):
        with self.captureOnCommitCallbacks(execute=True):
            participant_declined(self.app)
        self.assertEqual([m.to for m in mail.outbox], [['beheer@example.org']])

    def test_placement_and_waitlist_are_distinct(self):
        with self.captureOnCommitCallbacks(execute=True):
            placement_confirmed(self.app, 'Puppy zaterdag')
            application_closed(self.app, waitlisted=True)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Puppy zaterdag', mail.outbox[0].body)
        self.assertIn('wachtlijst', mail.outbox[1].subject.lower())

    def test_rolled_back_transaction_does_not_send_email(self):
        from django.db import transaction
        try:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                with transaction.atomic():
                    participant_confirmed(self.app)
                    raise ValueError('rollback')
        except ValueError:
            pass
        self.assertEqual(len(mail.outbox), 0)
