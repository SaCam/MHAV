from datetime import date

from django.test import TestCase

from .models import Season, TrainerSeasonAvailability


class TrainerAvailabilityStatusTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.trainer = User.objects.create_user(
            username="availability-trainer",
            email="trainer-availability@example.com",
            password="test-password",
        )
        self.season = Season.objects.create(
            name="Beschikbaarheid testseizoen",
            starts_on=date(2027, 3, 7),
            ends_on=date(2027, 5, 9),
            lesson_count=10,
            lesson_day="sun",
        )

    def test_partial_dates_have_four_distinct_states(self):
        dates = self.season.lesson_dates
        response = TrainerSeasonAvailability.objects.create(
            season=self.season,
            trainer=self.trainer,
            response="partial",
            date_statuses={
                dates[0].isoformat(): "yes",
                dates[1].isoformat(): "no",
                dates[2].isoformat(): "maybe",
                dates[3].isoformat(): "unset",
            },
            unavailable_dates=[dates[1].isoformat()],
        )
        self.assertEqual(
            [response.status_for_date(day) for day in dates[:5]],
            ["yes", "no", "maybe", "unset", "maybe"],
        )
        self.assertEqual(response.available_count, 1)
        response.full_clean()

    def test_all_and_none_override_legacy_dates(self):
        day = self.season.lesson_dates[0]
        response = TrainerSeasonAvailability(
            season=self.season,
            trainer=self.trainer,
            response="all",
        )
        self.assertEqual(response.status_for_date(day), "yes")
        self.assertEqual(response.available_count, 10)
        response.response = "none"
        self.assertEqual(response.status_for_date(day), "no")
        self.assertEqual(response.available_count, 0)

    def test_invalid_state_is_rejected(self):
        response = TrainerSeasonAvailability(
            season=self.season,
            trainer=self.trainer,
            response="partial",
            date_statuses={self.season.lesson_dates[0].isoformat(): "invalid"},
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            response.full_clean()
