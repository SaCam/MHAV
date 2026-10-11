from django.urls import path
from . import views

app_name = "content"
urlpatterns = [
    path("", views.news_list, name="list"),
    path("insturen/", views.submit_news, name="submit"),
    path("ingestuurd/", views.submitted, name="submitted"),
    path("<slug:slug>/", views.news_detail, name="detail"),
]
