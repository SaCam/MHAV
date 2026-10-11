from django.contrib import admin
from django.utils import timezone
from .models import Announcement, NewsPost


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body")
    list_editable = ("is_published",)


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "author", "published_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "summary", "body")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (("Inhoud", {"fields": ("title", "slug", "summary", "body", "image")}),
                 ("Publicatie", {"fields": ("status", "published_at", "author")}),
                 ("Overige gegevens", {"fields": ("created_at", "updated_at")}))

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
