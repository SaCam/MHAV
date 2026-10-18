from django.urls import path
from django.views.generic import TemplateView
from . import views
from apps.planning import views as planning_views
from apps.planning import email_verification

app_name = "website"
urlpatterns = [
    path("cookiebeleid/", TemplateView.as_view(template_name="website/cookie_policy.html"), name="cookie_policy"),
    path("", views.home, name="home"),
    path("homepage/opslaan/", views.home_edit, name="home_edit"),
    path("phv/", views.phv, name="phv"),
    path("phv/opslaan/", views.section_page_save, {"page_key": "phv"}, name="phv_save"),
    path("cursussen/", views.courses, name="courses"),
    path("inschrijven/", planning_views.public_application, name="application"),
    path("inschrijven/bedankt/", planning_views.application_thanks, name="application_thanks"),
    path("inschrijven/email-bevestigen/<str:token>/", email_verification.verify_application_email, name="application_verify_email"),
    path("inschrijven/bevestiging-opnieuw/", email_verification.resend_application_verification, name="application_resend_verification"),
    path("inschrijven/account-uitnodiging/", planning_views.request_account_invite, name="application_account_invite"),
    path("inschrijven/account-activeren/<str:token>/", planning_views.application_account_claim, name="application_account_claim"),
    path("cursussen/beheer/", views.course_manage, name="course_manage"),
    path("cursussen/beheer/nieuw/", views.course_form, name="course_new"),
    path("cursussen/beheer/<int:pk>/", views.course_form, name="course_edit"),
    path("cursussen/beheer/<int:pk>/verwijderen/", views.course_delete, name="course_delete"),
    path("cursussen/opslaan/", views.section_page_save, {"page_key": "courses"}, name="courses_save"),
    path("instructeurs/", views.instructors, name="instructors"),
    path("website/<str:page_key>/opslaan/", views.public_page_save, name="public_page_save"),
    path("algemeen/", views.general, name="general"),
    path("contact/", views.contact, name="contact"),
    path("contact/bedankt/", views.contact_thanks, name="contact_thanks"),
    path("informatie/", views.page_index, name="pages"),
    path("informatie/<slug:slug>/", views.page, name="page"),
]
