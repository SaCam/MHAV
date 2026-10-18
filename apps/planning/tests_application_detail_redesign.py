from django.template.loader import get_template
from django.test import SimpleTestCase


class ApplicationDetailRedesignTests(SimpleTestCase):
    def test_current_placement_is_visible(self):
        source = get_template('planning/application_detail.html').template.source
        self.assertIn('placement_group.season.name', source)
        self.assertIn('placement_group.name', source)
        self.assertIn('placement_state == \'concept\'', source)
        self.assertIn('placement_state == \'definitief\'', source)

    def test_actions_are_conditional(self):
        source = get_template('planning/application_detail.html').template.source
        self.assertIn('{% if can_change_draft %}', source)
        self.assertIn('{% if can_confirm_placement %}', source)
        self.assertIn('{% if needs_season_consent %}', source)

    def test_email_side_effects_are_explained(self):
        source = get_template('planning/application_detail.html').template.source
        self.assertIn('geen e-mail', source)
        self.assertIn('plaatsingsmail', source)
