from datetime import date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from .models import Season, TrainingGroup, TrainerSeasonAvailability


class GroupSchedulingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='planner-coverage', password='pass')
        self.trainer = User.objects.create_user(username='trainer-coverage', password='pass')
        self.admin.groups.add(Group.objects.get_or_create(name='MHAV - Administrator')[0])
        self.trainer.groups.add(Group.objects.get_or_create(name='MHAV - Trainer')[0])
        self.season = Season.objects.create(name='Zaterdag seizoen', starts_on=date(2027, 3, 6),
                                            ends_on=date(2027, 5, 8), lesson_count=10, lesson_day='sat')

    def test_only_draft_seasons_can_be_changed_by_trainer(self):
        self.client.force_login(self.trainer)
        url = reverse('planning:trainer_availability', args=[self.season.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.season.status = Season.Status.ACTIVE
        self.season.save(update_fields=['status'])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {'response': 'none'}).status_code, 404)
        overview = self.client.get(reverse('planning:trainer_seasons'))
        self.assertNotContains(overview, self.season.name)

    def test_group_requires_saturday_dates(self):
        group = TrainingGroup(season=self.season, name='Zaterdag A', course_name='B-cursus',
                              day='sat', starts_at='09:00', ends_at='10:00', capacity=10,
                              lesson_dates_selected=[self.season.lesson_dates[0].isoformat()])
        group.full_clean()
        group.save()
        self.assertEqual(len(group.scheduled_dates), 1)
        group.lesson_dates_selected = ['2027-04-04']
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            group.full_clean()

    def test_instructor_coverage_uses_confirmed_dates_only(self):
        from .views import _group_coverage
        days = self.season.lesson_dates
        TrainerSeasonAvailability.objects.create(season=self.season, trainer=self.trainer,
            response='partial', date_statuses={days[0].isoformat(): 'yes', days[1].isoformat(): 'maybe'})
        rows = _group_coverage(self.season, [days[0].isoformat(), days[1].isoformat()], self.trainer.pk)
        self.assertEqual([row['state'] for row in rows], ['yes', 'maybe'])
