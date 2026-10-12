"""Regression tests for the v21a.2 availability validation fix."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .models import Season, TrainerSeasonAvailability


class TrainerAvailabilityValidationTests(SimpleTestCase):
    def setUp(self):
        self.season = Season(
            pk=1,
            name="Testseizoen",
            starts_on=date(2027, 3, 7),
            ends_on=date(2027, 3, 21),
            lesson_count=3,
            lesson_day="sun",
        )
        self.dates = [day.isoformat() for day in self.season.lesson_dates]

    def make_availability(self, response, statuses, unavailable):
        item = TrainerSeasonAvailability(
            response=response,
            date_statuses=statuses,
            unavailable_dates=unavailable,
        )
        item.season = self.season
        return item

    def test_none_accepts_all_unavailable_dates(self):
        item = self.make_availability(
            TrainerSeasonAvailability.Response.NONE,
            {day: "no" for day in self.dates},
            self.dates,
        )
        item.clean()
        self.assertEqual(item.available_count, 0)

    def test_all_accepts_all_available_dates(self):
        item = self.make_availability(
            TrainerSeasonAvailability.Response.ALL,
            {day: "yes" for day in self.dates},
            [],
        )
        item.clean()
        self.assertEqual(item.available_count, 3)

    def test_partial_accepts_mixed_statuses(self):
        item = self.make_availability(
            TrainerSeasonAvailability.Response.PARTIAL,
            dict(zip(self.dates, ("yes", "no", "maybe"))),
            [self.dates[1]],
        )
        item.clean()
        self.assertEqual(item.available_count, 1)

    def test_invalid_date_is_rejected(self):
        item = self.make_availability(
            TrainerSeasonAvailability.Response.NONE,
            {day: "no" for day in self.dates},
            ["2030-01-01"],
        )
        with self.assertRaises(ValidationError):
            item.clean()
