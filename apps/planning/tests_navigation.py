from .tests_offering_helpers import create_open_offering
from django.test import TestCase
from django.urls import reverse
from apps.website.models import SitePage


class RegistrationNavigationTests(TestCase):
    def setUp(self):
        self.course, _ = SitePage.objects.update_or_create(
            slug="b-cursus",
            defaults={
                "title": "B-cursus",
                "is_published": True,
            },
        )
        self.offering = create_open_offering(self.course)

    def test_course_page_links_to_prefilled_registration(self):
        response = self.client.get(reverse("website:page", args=[self.course.slug]))
        self.assertContains(response, f"?course={self.course.pk}")
        form_response = self.client.get(reverse("website:application"), {"course": self.course.pk})
        self.assertEqual(form_response.context["form"].initial["course"], self.course.pk)

    def test_old_registration_info_redirects_to_form(self):
        self.assertRedirects(self.client.get("/informatie/inschrijven/"), reverse("website:application"))

    def test_unpublished_course_is_not_prefilled(self):
        self.course.is_published = False
        self.course.save(update_fields=["is_published"])
        response = self.client.get(reverse("website:application"), {"course": self.course.pk})
        self.assertNotIn("course", response.context["form"].initial)
