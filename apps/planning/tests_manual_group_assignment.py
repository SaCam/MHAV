from types import SimpleNamespace
from django.test import SimpleTestCase
from .application_planning import manually_assignable_groups, compatible_groups


class ManualGroupAssignmentTests(SimpleTestCase):
    def application(self, preferences=None, season_id=1):
        return SimpleNamespace(time_preferences=preferences or {}, course_id=10, season_id=season_id)

    def group(self, pk=5, season_id=1):
        return SimpleNamespace(pk=pk, course_id=10, season_id=season_id,
                               execution_status='planned', starts_at='10:00')

    def test_no_preference_allows_manual_group_placement(self):
        group = self.group()
        self.assertEqual(manually_assignable_groups(self.application(), [group]), [group])

    def test_automatic_proposals_still_require_explicit_availability_for_season(self):
        self.assertEqual(compatible_groups(self.application(), [self.group()]), [])

    def test_manual_override_allows_unavailable_time(self):
        self.assertEqual(manually_assignable_groups(self.application({'5': 'unavailable'}), [self.group()]), [self.group()])

    def test_other_season_is_available_to_administrator(self):
        self.assertEqual(manually_assignable_groups(self.application(), [self.group(season_id=2)]), [self.group(season_id=2)])

    def test_preferred_group_is_listed_first(self):
        groups = [self.group(5), self.group(6)]
        self.assertEqual([g.pk for g in manually_assignable_groups(
            self.application({'5': 'ok', '6': 'preferred'}), groups)], [6, 5])
