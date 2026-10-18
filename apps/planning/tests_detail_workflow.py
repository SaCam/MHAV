from django.test import SimpleTestCase
from .forms import ApplicationReviewForm
from .models import CourseApplication


class ApplicationDetailWorkflowTests(SimpleTestCase):
    def test_review_form_cannot_silently_change_status(self):
        self.assertNotIn('status', ApplicationReviewForm.base_fields)
        self.assertIn('admin_notes', ApplicationReviewForm.base_fields)

    def test_waitlist_is_distinct_from_placed(self):
        self.assertNotEqual(CourseApplication.Status.WAITLIST, CourseApplication.Status.PROCESSED)
