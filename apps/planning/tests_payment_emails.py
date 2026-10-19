from datetime import date, time
from types import SimpleNamespace
from django.test import SimpleTestCase
from .payment_emails import payment_received_body


class PaymentReceiptTextTests(SimpleTestCase):
    def test_receipt_has_real_group_and_first_training(self):
        group = SimpleNamespace(name='C-cursus (11.00)', first_lesson_date=date(2026, 10, 31), starts_at=time(11), ends_at=time(12))
        app = SimpleNamespace(first_name='Jenneke', last_name='Test', dog_name='Rosa', dog_profile_id=None, course_id=1, course=SimpleNamespace(title='C-cursus'), linked_enrollment=SimpleNamespace(group=group))
        payment = SimpleNamespace(application=app, amount_due='75.00', reference='MHAV-000056')
        body = payment_received_body(payment)
        for text in ('Rosa', 'C-cursus (11.00)', 'zaterdag 31 oktober 2026', '11:00 - 12:00', '€ 75,00', 'MHAV-000056'):
            self.assertIn(text, body)

    def test_missing_first_training_does_not_invent_date(self):
        group = SimpleNamespace(name='Zaterdaggroep', first_lesson_date=None, starts_at=time(11), ends_at=time(12))
        app = SimpleNamespace(first_name='Jan', last_name='Test', dog_name='Rex', dog_profile_id=None, course_id=1, course=SimpleNamespace(title='C-cursus'), linked_enrollment=SimpleNamespace(group=group))
        body = payment_received_body(SimpleNamespace(application=app, amount_due='50.00', reference='REF'))
        self.assertIn('nog bekendgemaakt', body)
        self.assertNotIn('11:00 - 12:00', body)
