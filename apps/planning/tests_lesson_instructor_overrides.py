from datetime import date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from .forms import TrainingGroupForm
from .models import Season, TrainingGroup, TrainerSeasonAvailability, LessonInstructorOverride


class LessonInstructorOverrideTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='planner-replacement', password='pass')
        self.available = User.objects.create_user(username='available-replacement', password='pass')
        self.unavailable = User.objects.create_user(username='unavailable-replacement', password='pass')
        admin_group, _ = Group.objects.get_or_create(name='MHAV - Administrator')
        trainer_group, _ = Group.objects.get_or_create(name='MHAV - Trainer')
        self.admin.groups.add(admin_group)
        self.available.groups.add(trainer_group)
        self.unavailable.groups.add(trainer_group)
        self.season = Season.objects.create(name='Replacement season', starts_on=date(2027, 3, 6),
                                            ends_on=date(2027, 3, 13), lesson_count=2, lesson_day='sat')
        self.day = self.season.lesson_dates[0]
        self.group = TrainingGroup.objects.create(season=self.season, name='Group R', course_name='B-cursus',
            trainer=self.available, day='sat', starts_at='09:00', ends_at='10:00', capacity=10,
            lesson_dates_selected=[self.day.isoformat()])

    def test_group_dropdown_requires_confirmed_availability(self):
        form = TrainingGroupForm(season=self.season)
        self.assertNotIn(self.available, form.fields['trainer'].queryset)
        TrainerSeasonAvailability.objects.create(season=self.season, trainer=self.available,
            response='partial', date_statuses={self.day.isoformat(): 'yes'})
        TrainerSeasonAvailability.objects.create(season=self.season, trainer=self.unavailable,
            response='none', date_statuses={d.isoformat(): 'no' for d in self.season.lesson_dates})
        form = TrainingGroupForm(season=self.season)
        self.assertIn(self.available, form.fields['trainer'].queryset)
        self.assertNotIn(self.unavailable, form.fields['trainer'].queryset)

    def test_replacement_can_be_assigned_without_availability_and_confirmed(self):
        self.client.force_login(self.admin)
        url = reverse('planning:lesson_instructor_override', args=[self.group.pk, self.day.isoformat()])
        response = self.client.post(url, {'trainer': str(self.unavailable.pk)})
        self.assertEqual(response.status_code, 302)
        replacement = LessonInstructorOverride.objects.get(group=self.group, lesson_date=self.day)
        self.assertFalse(replacement.offline_confirmed)
        self.assertContains(self.client.get(reverse('planning:group_detail', args=[self.group.pk])), 'Wacht op offline bevestiging')
        self.client.post(url, {'trainer': str(self.unavailable.pk), 'offline_confirmed': 'on'})
        replacement.refresh_from_db()
        self.assertTrue(replacement.offline_confirmed)
        self.client.post(url, {'trainer': ''})
        self.assertFalse(LessonInstructorOverride.objects.filter(group=self.group).exists())

    def test_unscheduled_date_rejected(self):
        self.client.force_login(self.admin)
        url = reverse('planning:lesson_instructor_override', args=[self.group.pk, self.season.lesson_dates[1].isoformat()])
        self.assertEqual(self.client.post(url, {'trainer': str(self.unavailable.pk)}).status_code, 404)
