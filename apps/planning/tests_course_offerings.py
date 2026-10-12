from datetime import date, time, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.website.models import SitePage
from .models import Season, TrainingGroup, SeasonCourseOffering, TrainerSeasonAvailability


class OfferingReadinessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='course_test_trainer', password='test-pass')
        self.season = Season.objects.create(name='Test course approval 2027', starts_on=date(2027, 1, 2), ends_on=date(2027, 3, 6), lesson_count=10, lesson_day='sat')
        self.course = SitePage.objects.create(slug='cursus-test-approval', title='Test cursus', is_published=True)
        self.group = TrainingGroup.objects.create(season=self.season, course=self.course, name='Groep 09:00', day='sat', starts_at=time(9), ends_at=time(10), capacity=10, trainer=self.user, lesson_dates_selected=[date(2027, 1, 2).isoformat()])
        self.offering = SeasonCourseOffering.objects.create(season=self.season, course=self.course)

    def test_missing_coverage_requires_reason(self):
        snapshot = self.offering.planning_snapshot()
        self.assertFalse(snapshot['issues'])
        self.assertEqual(len(snapshot['uncovered']), 1)
        self.offering.approved = True
        self.offering.coverage_override = True
        self.offering.approval_signature = snapshot['signature']
        self.assertFalse(self.offering.approval_valid())
        self.offering.override_reason = 'Vervanging telefonisch geregeld'
        self.assertTrue(self.offering.approval_valid())

    def test_planning_change_invalidates_approval(self):
        snap = self.offering.planning_snapshot()
        self.offering.approved = True
        self.offering.coverage_override = True
        self.offering.override_reason = 'Vervanging wordt geregeld'
        self.offering.approval_signature = snap['signature']
        self.offering.registration_open = True
        self.assertTrue(self.offering.accepts_applications())
        self.group.starts_at = time(10)
        self.group.save()
        self.assertFalse(self.offering.accepts_applications())

    def test_confirmed_availability_allows_approval_without_override(self):
        TrainerSeasonAvailability.objects.create(season=self.season, trainer=self.user, response='all', date_statuses={date(2027, 1, 2).isoformat(): 'yes'})
        snap = self.offering.planning_snapshot()
        self.assertFalse(snap['uncovered'])
        self.offering.approved = True
        self.offering.approval_signature = snap['signature']
        self.assertTrue(self.offering.approval_valid())
