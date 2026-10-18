from django.core import signing
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import CourseApplication
from .email_verification import SALT
from .season_recommendations import suitable_seasons


class ParticipantConfirmationTests(TestCase):
    def setUp(self):
        self.app = CourseApplication.objects.create(
            first_name='Cursist', last_name='Test', email='cursist@example.org',
            dog_name='Bello', privacy_accepted_at=timezone.now(),
            submission_source='admin', status=CourseApplication.Status.PENDING_CONFIRMATION)
        token = signing.dumps({'id': self.app.pk, 'email': self.app.email.lower()}, salt=SALT)
        self.url = reverse('website:application_verify_email', args=[token])

    def test_admin_application_is_pending_until_explicit_confirmation(self):
        self.assertEqual(self.app.status, CourseApplication.Status.PENDING_CONFIRMATION)
        self.assertIsNone(self.app.participant_confirmed_at)
        self.assertEqual(suitable_seasons(self.app), [])
        self.client.get(self.url)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, CourseApplication.Status.PENDING_CONFIRMATION)
        self.client.post(self.url, {'decision': 'confirm'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, CourseApplication.Status.NEW)
        self.assertIsNotNone(self.app.email_verified_at)
        self.assertIsNotNone(self.app.participant_confirmed_at)

    def test_participant_can_decline_and_cannot_reactivate_using_old_link(self):
        self.client.post(self.url, {'decision': 'decline'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, CourseApplication.Status.DECLINED)
        self.assertIsNotNone(self.app.participant_declined_at)
        self.client.post(self.url, {'decision': 'confirm'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, CourseApplication.Status.DECLINED)

    def test_confirm_and_create_account_redirects_to_existing_secure_password_flow(self):
        response = self.client.post(self.url, {'decision': 'confirm', 'create_account': 'on'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/account-activeren/', response.url)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, CourseApplication.Status.NEW)
        self.assertIsNone(self.app.user_id)

    def test_confirmed_application_cannot_be_declined_later(self):
        self.client.post(self.url, {'decision': 'confirm'})
        self.client.post(self.url, {'decision': 'decline'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, CourseApplication.Status.NEW)
