from django.shortcuts import render
from apps.content.models import Announcement


def home(request):
    announcements = Announcement.objects.filter(is_published=True).order_by("-published_at", "-created_at")[:3]
    return render(request, "website/home.html", {"announcements": announcements})
