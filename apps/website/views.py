from django.shortcuts import render
from apps.content.models import Announcement, NewsPost


def home(request):
    announcements = Announcement.objects.filter(is_published=True).order_by("-published_at", "-created_at")[:3]
    news_posts = NewsPost.public().order_by("-published_at", "-created_at")[:3]
    return render(request, "website/home.html", {"announcements": announcements, "news_posts": news_posts})
