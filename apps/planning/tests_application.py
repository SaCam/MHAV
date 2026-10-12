from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from apps.website.models import SitePage
from .models import CourseApplication, Season, TrainingGroup
from .tests_offering_helpers import create_open_offering


class PublicApplicationTests(TestCase):
    def setUp(self):
        self.course, _ = SitePage.objects.get_or_create(slug='puppycursus', defaults={'title': 'Puppycursus', 'is_published': True})
        if not self.course.is_published:
            self.course.is_published = True
            self.course.save(update_fields=['is_published'])
        self.offering = create_open_offering(self.course)
        self.url = reverse('website:application')
        self.data = {
            'first_name': 'Test', 'last_name': 'Cursist', 'email': 'test@example.org',
            'phone': '0612345678', 'street': 'Teststraat', 'house_number': '12',
            'postal_code': '5555 AA', 'city': 'Valkenswaard', 'dog_name': 'Bello',
            'dog_breed': 'Kruising', 'course': str(self.course.pk),
            'privacy_agreement': 'on', 'season': str(self.offering.season_id),
        }

    def test_anonymous_can_apply_without_creating_placement(self):
        data = self.data.copy()
        data['country'] = 'NL'

        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('website:application_thanks'))
        application = CourseApplication.objects.get()
        self.assertEqual(application.status, CourseApplication.Status.NEW)
        self.assertEqual(application.email, 'test@example.org')
        self.assertIsNotNone(application.privacy_accepted_at)
        self.assertIsNone(application.linked_enrollment)

    def test_closed_offering_rejects_application(self):
        self.offering.registration_open = False
        self.offering.save(update_fields=['registration_open'])
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_planning_change_invalidates_registration(self):
        group = TrainingGroup.objects.get(season=self.offering.season, course=self.course)
        group.starts_at = '10:00'
        group.save()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_consent_required(self):
        data = self.data.copy()
        data.pop('privacy_agreement')
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_honeypot_rejects_submission(self):
        data = {**self.data, 'website': 'https://spam.invalid'}
        self.client.post(self.url, data)
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_unpublished_course_rejected(self):
        self.course.is_published = False
        self.course.save()
        self.client.post(self.url, self.data)
        self.assertEqual(CourseApplication.objects.count(), 0)

    def test_admin_queue_requires_admin_role(self):
        self.assertEqual(self.client.get(reverse('planning:application_list')).status_code, 302)

    def test_extra_dog_details_saved(self):
        data = {**self.data, 'dog_origin':'shelter', 'dog_count':'two', 'middle_name':'van', 'country':'NL', 'trained_before':'true'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        application = CourseApplication.objects.get()
        self.assertEqual(application.dog_origin, 'shelter')
        self.assertEqual(application.dog_count, 'two')
        self.assertEqual(application.middle_name, 'van')

    def test_account_invitation_requires_session_application(self):
        from django.core import mail
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('website:application_account_invite'))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(len(mail.outbox), 0)
