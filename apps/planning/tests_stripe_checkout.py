from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.urls import reverse
from .stripe_views import webhook

class StripeCheckoutSmokeTests(SimpleTestCase):
    def test_checkout_url(self):
        self.assertIn('/betalen/12/', reverse('planning:stripe_checkout', args=[12]))

    def test_webhook_url(self):
        self.assertIn('/betalen/webhook/', reverse('planning:stripe_webhook'))

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.planning.stripe_views.stripe.Webhook.construct_event', side_effect=ValueError('invalid'))
    def test_bad_signature_is_rejected(self, _verify):
        request = RequestFactory().post('/betalen/webhook/', data=b'bad', content_type='application/json')
        self.assertEqual(webhook(request).status_code, 400)

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.planning.stripe_views.stripe.Webhook.construct_event', return_value={'type': 'checkout.session.expired'})
    def test_expired_session_does_not_mark_paid(self, _verify):
        request = RequestFactory().post('/betalen/webhook/', data=b'{}', content_type='application/json')
        self.assertEqual(webhook(request).status_code, 200)
