"""Regression coverage for confirmation gates, price gates and account links."""
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from unittest.mock import patch

from apps.accounts.forms import EmailLoginForm
from .finalization import inspect_application
from .payments import payment_price_problem


class AccountVerificationBehaviorTests(TestCase):
    def setUp(self):
        self.password = 'A-strong-test-password-2026!'
        self.user = get_user_model().objects.create_user(
            username='mhav_inactive_test',
            email='inactive@example.org',
            password=self.password,
            is_active=False,
        )

    def test_inactive_account_with_correct_password_has_clear_message(self):
        form = EmailLoginForm(data={
            'username': self.user.email,
            'password': self.password,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('nog niet geactiveerd', str(form.non_field_errors()))

    def test_incorrect_password_does_not_reveal_activation_status(self):
        form = EmailLoginForm(data={
            'username': self.user.email,
            'password': 'wrong-password',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn('nog niet geactiveerd', str(form.non_field_errors()))

    def test_second_click_on_account_activation_is_friendly(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse('website:application_account_verify', args=[uid, token])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account al geactiveerd')


class DefinitivePlacementGuardsTests(TestCase):
    def test_unconfirmed_application_is_blocked_before_identity_resolution(self):
        app = SimpleNamespace(email_verified_at=None, participant_confirmed_at=None)
        self.assertIn('niet geverifieerd', inspect_application(app, None))
        app.email_verified_at = object()
        self.assertIn('niet bevestigd', inspect_application(app, None))

    def test_missing_course_price_is_explicit_error(self):
            application = SimpleNamespace(
                course_id=999999,
            )

            group = SimpleNamespace(
                season_id=999999,
            )

            with patch(
                "apps.planning.payments.SeasonCourseOffering.objects.filter"
            ) as mock_filter:
                mock_filter.return_value.first.return_value = None

                result = payment_price_problem(
                    application,
                    group,
                )

            self.assertIn("Geen cursusprijs", result)