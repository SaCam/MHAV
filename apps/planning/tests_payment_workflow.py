from django.test import SimpleTestCase
from django.urls import reverse
from .models import RegistrationPayment

class PaymentWorkflowSmokeTests(SimpleTestCase):
    def test_payment_statuses(self):
        self.assertIn(('pending', 'Nog te betalen'), RegistrationPayment.Status.choices)
        self.assertIn(('paid', 'Betaald'), RegistrationPayment.Status.choices)
    def test_admin_payment_url(self):
        self.assertTrue(reverse('planning:application_payment', args=[50]).endswith('/aanmeldingen/50/betaling/'))
