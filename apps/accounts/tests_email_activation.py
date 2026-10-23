from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountEmailActivationTests(TestCase):
    def test_register_requires_email_activation_and_does_not_login(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('accounts:register'), {
                'first_name': 'Test',
                'last_name': 'Persoon',
                'email': 'test@example.com',
                'password1': 'AnExamplePassword!2026',
                'password2': 'AnExamplePassword!2026',
            })
        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.get(email='test@example.com')
        self.assertFalse(user.is_active)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Bevestig je e-mailadres', mail.outbox[0].subject)
        self.assertIn('/inschrijven/account-verifieren/', mail.outbox[0].body)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = reverse('website:application_account_verify', args=[uid, token])
        self.client.get(url)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_reset_email_is_sent_for_active_account(self):
        get_user_model().objects.create_user(
            username='mhav_reset_test', email='reset@example.com',
            password='AnExamplePassword!2026', is_active=True)
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'reset@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Wachtwoord opnieuw instellen', mail.outbox[0].subject)
        self.assertIn('/account/wachtwoord-herstellen/', mail.outbox[0].body)
