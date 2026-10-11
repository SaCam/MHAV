from django.contrib import admin
from .models import MemberProfile


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_approved", "joined_at")
    list_filter = ("is_approved",)
    list_editable = ("is_approved",)
    search_fields = ("user__username", "user__email")
