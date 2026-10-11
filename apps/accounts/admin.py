from django.contrib import admin
from .models import MemberProfile

@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "joined_at")
    search_fields = ("user__username", "user__email")
