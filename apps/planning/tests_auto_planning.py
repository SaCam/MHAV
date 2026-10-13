from types import SimpleNamespace
from django.test import SimpleTestCase
from .application_planning import compatible_groups

class CompatibilityTests(SimpleTestCase):
    def setUp(self):
        self.group = SimpleNamespace(pk=5, course_id=2, season_id=3, starts_at='09:00')
    def test_preference_is_required(self):
        app = SimpleNamespace(course_id=2, season_id=3, time_preferences={})
        self.assertEqual(compatible_groups(app, [self.group]), [])
    def test_preferred_group_is_eligible(self):
        app = SimpleNamespace(course_id=2, season_id=3, time_preferences={'5':'preferred'})
        self.assertEqual(compatible_groups(app, [self.group])[0][1], self.group)
    def test_unavailable_group_is_excluded(self):
        app = SimpleNamespace(course_id=2, season_id=3, time_preferences={'5':'unavailable'})
        self.assertEqual(compatible_groups(app, [self.group]), [])
