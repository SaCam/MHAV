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
            'postal_code': '5555 AA', 'city': 'Valkenswaard', 'country': 'NL', 'dog_name': 'Bello',
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

    def test_open_application_without_season(self):
        data = {**self.data, 'season': ''}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('website:application_thanks'))
        application = CourseApplication.objects.get()
        self.assertIsNone(application.season_id)
        self.assertEqual(application.course_id, self.course.pk)

    def test_open_application_when_registration_closed(self):
        self.offering.registration_open = False
        self.offering.save(update_fields=['registration_open'])
        data = {**self.data, 'season': ''}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('website:application_thanks'))
        self.assertIsNone(CourseApplication.objects.get().season_id)

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


class RegistrationV2IdentityTests(PublicApplicationTests):
    def test_guest_source_recorded(self):
        self.client.post(self.url, self.data)
        app = CourseApplication.objects.get()
        self.assertEqual(app.submission_source, 'guest')
        self.assertIsNone(app.submitted_by_id)

    def test_logged_in_identity_cannot_be_forged(self):
        User = get_user_model()
        user = User.objects.create_user(username='memberv2', password='test-password', email='member@example.org', first_name='Member', last_name='Example')
        self.client.force_login(user)
        self.client.post(self.url, {**self.data, 'first_name': 'Imposter', 'email': 'other@example.org'})
        app = CourseApplication.objects.get()
        self.assertEqual(app.email, user.email)
        self.assertEqual(app.first_name, user.first_name)
        self.assertEqual(app.user_id, user.pk)
        self.assertEqual(app.submitted_by_id, user.pk)
        self.assertEqual(app.submission_source, 'member')

    def test_anonymous_cannot_submit_on_behalf(self):
        response = self.client.post(reverse('planning:application_on_behalf'), self.data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CourseApplication.objects.exists())

    def test_admin_can_submit_for_another_person(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='adminv2', password='test-password', email='admin@example.org')
        self.client.force_login(admin)
        response = self.client.post(reverse('planning:application_on_behalf'), self.data)
        self.assertEqual(response.status_code, 302)
        app = CourseApplication.objects.get()
        self.assertEqual(app.email, self.data['email'])
        self.assertIsNone(app.user_id)
        self.assertEqual(app.submitted_by_id, admin.pk)
        self.assertEqual(app.submission_source, 'admin')
