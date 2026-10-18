from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CourseApplication
from .views import _claim_signer


class ExistingAccountClaimTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='claim_owner', email='owner@example.org', password='strong-test-password')
        self.other = User.objects.create_user(username='claim_other', email='other@example.org', password='strong-test-password')
        self.application = CourseApplication.objects.create(
            first_name='Owner',
            last_name='Example',
            email='owner@example.org',
            dog_name='Bello',
            privacy_accepted_at=timezone.now(),
        )
        self.url = reverse('website:application_account_claim', args=[_claim_signer().sign(str(self.application.pk))])

    def test_logged_in_owner_can_claim_after_email_verification(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('accounts:dashboard'))
        self.application.refresh_from_db()
        self.assertEqual(self.application.user_id, self.owner.pk)

    def test_other_account_cannot_claim(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.user_id)

    def test_anonymous_cannot_claim_existing_account(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.user_id)

    def test_expired_or_invalid_token_rejected(self):
        response = self.client.get(reverse('website:application_account_claim', args=['invalid-token']))
        self.assertEqual(response.status_code, 404)
