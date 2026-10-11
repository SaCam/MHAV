from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body")
    list_editable = ("is_published",)
