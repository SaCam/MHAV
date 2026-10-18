from django.core import mail
from django.core import signing
from django.test import TestCase, override_settings, RequestFactory
from django.urls import reverse
from django.utils import timezone
from .models import CourseApplication
from .email_verification import verification_url, send_application_verification, SALT

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailVerificationTests(TestCase):
    def setUp(self):
        self.app = CourseApplication.objects.create(
            first_name='Test', last_name='Deelnemer', email='test@example.org',
            dog_name='Bello', privacy_accepted_at=timezone.now())
        self.link = verification_url(RequestFactory().get('/', HTTP_HOST='testserver'), self.app)
        self.path = self.link.split('testserver', 1)[-1]

    def test_send_mail_does_not_create_account(self):
        self.assertTrue(send_application_verification(RequestFactory().get('/', HTTP_HOST='testserver'), self.app))
        self.assertEqual(len(mail.outbox), 1)
        self.app.refresh_from_db()
        self.assertIsNone(self.app.user_id)
        self.assertIsNone(self.app.email_verified_at)

    def test_confirm_requires_post_and_is_idempotent(self):
        self.assertEqual(self.client.get(self.path).status_code, 200)
        self.app.refresh_from_db()
        self.assertIsNone(self.app.email_verified_at)
        self.assertEqual(self.client.post(self.path).status_code, 200)
        self.app.refresh_from_db()
        first = self.app.email_verified_at
        self.assertIsNotNone(first)
        self.client.post(self.path)
        self.app.refresh_from_db()
        self.assertEqual(self.app.email_verified_at, first)

    def test_invalid_token_is_rejected(self):
        self.assertEqual(self.client.get(reverse('website:application_verify_email', args=['invalid'])).status_code, 404)

    def test_changed_email_invalidates_link(self):
        self.app.email = 'changed@example.org'
        self.app.save(update_fields=['email'])
        self.assertEqual(self.client.post(self.path).status_code, 404)
