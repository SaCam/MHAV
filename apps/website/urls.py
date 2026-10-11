from django.urls import path
from . import views

app_name = "website"
urlpatterns = [
    path("", views.home, name="home"),
    path("homepage/opslaan/", views.home_edit, name="home_edit"),
    path("phv/", views.phv, name="phv"),
    path("phv/opslaan/", views.section_page_save, {"page_key": "phv"}, name="phv_save"),
    path("cursussen/", views.courses, name="courses"),
    path("cursussen/beheer/", views.course_manage, name="course_manage"),
    path("cursussen/beheer/nieuw/", views.course_form, name="course_new"),
    path("cursussen/beheer/<int:pk>/", views.course_form, name="course_edit"),
    path("cursussen/beheer/<int:pk>/verwijderen/", views.course_delete, name="course_delete"),
    path("cursussen/opslaan/", views.section_page_save, {"page_key": "courses"}, name="courses_save"),
    path("instructeurs/", views.instructors, name="instructors"),
    path("algemeen/", views.general, name="general"),
    path("contact/", views.contact, name="contact"),
    path("contact/bedankt/", views.contact_thanks, name="contact_thanks"),
    path("informatie/", views.page_index, name="pages"),
    path("informatie/<slug:slug>/", views.page, name="page"),
]
