from django.test import SimpleTestCase
from django.urls import reverse
from .payment_lifecycle import withdrawal_signer

class PaymentDeadlineRoutesTests(SimpleTestCase):
    def test_decline_route(self):
        token = withdrawal_signer().sign('12')
        self.assertIn('/betalen/afwijzen/', reverse('planning:payment_decline', args=[token]))
    def test_management_route(self):
        self.assertIn('/aanmeldingen/12/betaling/beheren/', reverse('planning:payment_deadline_manage', args=[12]))
