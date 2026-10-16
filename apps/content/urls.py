from django.urls import path
from . import views

app_name = "content"
urlpatterns = [
    path("mededelingen/", views.manage_announcements, name="announcements_manage"),
    path("mededelingen/nieuw/", views.edit_announcement, name="announcement_new"),
    path("mededelingen/<int:pk>/bewerken/", views.edit_announcement, name="announcement_edit"),
    path("mededelingen/<int:pk>/gelezen/", views.announcement_read, name="announcement_read"),
    path("", views.news_list, name="list"),
    path("insturen/", views.submit_news, name="submit"),
    path("ingestuurd/", views.submitted, name="submitted"),
    path("<slug:slug>/", views.news_detail, name="detail"),
]
