from django.conf import settings
from django.db import models

class MemberProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member_profile")
    is_approved = models.BooleanField("Lidmaatschap bevestigd", default=False)
    phone = models.CharField(max_length=30, blank=True)
    joined_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.get_username()
