from django.contrib import admin
from .models import SitePage


@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "menu_order")
    list_editable = ("is_published", "menu_order")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body")


from .models import WebsiteImage, Instructor


@admin.register(WebsiteImage)
class WebsiteImageAdmin(admin.ModelAdmin):
    list_display = ("title", "key", "image")
    search_fields = ("title", "key")
    readonly_fields = ("key",)


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_visible", "order")
    list_editable = ("is_visible", "order")
    search_fields = ("name", "role", "biography")


from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "created_at", "handled")
    list_filter = ("handled", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "created_at")
    list_editable = ("handled",)
