"""Regression tests: guest email is never enough to claim a member account."""
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.test import TestCase
from .finalization import resolve_identity


class FinalizationIdentityTests(TestCase):
    def app(self, **overrides):
        values = dict(email='member@example.org', first_name='Test', last_name='Member',
                      user_id=None, user=None, dog_name='Bello', dog_breed='',
                      dog_birth_date=None, dog_notes='', dog_profile_id=None,
                      linked_combination_id=None)
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_guest_email_cannot_claim_existing_account(self):
        user = get_user_model().objects.create_user(
            username='member', email='member@example.org',
            first_name='Test', last_name='Member')
        for create in (False, True):
            resolved, dog, combo, error = resolve_identity(self.app(), create=create)
            self.assertIsNone(resolved)
            self.assertIsNone(dog)
            self.assertIsNone(combo)
            self.assertIn('verifiëren', error)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_verified_link_can_reuse_existing_account(self):
        user = get_user_model().objects.create_user(
            username='member', email='member@example.org',
            first_name='Test', last_name='Member')
        resolved, _, _, error = resolve_identity(self.app(user_id=user.pk, user=user))
        self.assertEqual(resolved, user)
        self.assertIsNone(error)

    def test_verified_link_rejects_changed_email(self):
        user = get_user_model().objects.create_user(
            username='member', email='other@example.org',
            first_name='Test', last_name='Member')
        _, _, _, error = resolve_identity(self.app(user_id=user.pk, user=user))
        self.assertIn('niet overeen', error)
