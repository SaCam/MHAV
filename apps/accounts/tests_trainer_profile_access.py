from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class TrainerProfileAccessTests(TestCase):
    def test_superuser_can_open_trainer_profile(self):
        user = get_user_model().objects.create_superuser(username="mhav_admin_test", email="admin@example.com", password="test-password")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:trainer_profile")).status_code, 200)

    def test_regular_member_cannot_open_trainer_profile(self):
        user = get_user_model().objects.create_user(username="mhav_member_test", password="test-password")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:trainer_profile")).status_code, 403)

    def test_trainer_can_open_trainer_profile(self):
        user = get_user_model().objects.create_user(username="mhav_trainer_test", password="test-password")
        group, _ = Group.objects.get_or_create(name="MHAV - Trainer")
        user.groups.add(group)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:trainer_profile")).status_code, 200)
