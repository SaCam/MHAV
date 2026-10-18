from types import SimpleNamespace
from django.test import SimpleTestCase
from .models import CourseApplication
from .season_recommendations import suitable_seasons


class SeasonRecommendationSafetyTests(SimpleTestCase):
    def application(self, **overrides):
        data = {
            'start_preference': CourseApplication.StartPreference.FLEXIBLE,
            'linked_enrollment_id': None,
            'proposed_group_id': None,
            'alternative_season_id': None,
            'alternative_accepted_at': None,
            'status': CourseApplication.Status.NEW,
            'course_id': None,
        }
        data.update(overrides)
        return SimpleNamespace(**data)

    def test_specific_season_is_never_automatically_recommended(self):
        self.assertEqual(suitable_seasons(self.application(
            start_preference=CourseApplication.StartPreference.SPECIFIC)), [])

    def test_placed_application_is_not_eligible(self):
        self.assertEqual(suitable_seasons(self.application(linked_enrollment_id=10)), [])

    def test_pending_alternative_is_not_overridden(self):
        self.assertEqual(suitable_seasons(self.application(alternative_season_id=3)), [])

    def test_no_course_is_not_eligible(self):
        self.assertEqual(suitable_seasons(self.application()), [])
