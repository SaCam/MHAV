from .tests_offering_helpers import create_open_offering
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from apps.website.models import SitePage
from apps.planning.models import CourseApplication


class RegistrationCompatibilityTests(TestCase):
    def setUp(self):
        self.course, _ = SitePage.objects.update_or_create(
            slug="b-cursus",
            defaults={
                "title": "B-cursus",
                "is_published": True,
            },
        )
        self.offering = create_open_offering(self.course)

    def test_course_prefill(self):
        response = self.client.get(reverse('website:application'), {'course': self.course.pk})
        self.assertEqual(response.context['form'].initial['course'], self.course.pk)

    def test_unpublished_course_not_prefilled(self):
        self.course.is_published = False
        self.course.save(update_fields=['is_published'])
        response = self.client.get(reverse('website:application'), {'course': self.course.pk})
        self.assertNotIn('course', response.context['form'].initial)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_account_invitation_without_session_does_not_send_email(self):
        response = self.client.post(reverse('website:application_account_invite'))
        self.assertRedirects(response, reverse('website:application_thanks'))
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmation_without_session_does_not_claim_application(self):
        response = self.client.get(reverse('website:application_thanks'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['application'])
