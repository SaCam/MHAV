from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone
from .models import Announcement


def active_announcements(request):
    now = timezone.now()
    announcements = (Announcement.objects.filter(is_published=True, published_at__lte=now)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .annotate(priority_rank=Case(When(priority='urgent', then=Value(0)),
                                     When(priority='important', then=Value(1)),
                                     default=Value(2), output_field=IntegerField()))
        .order_by('priority_rank', '-published_at', '-pk'))
    unread = [item for item in announcements
              if request.COOKIES.get(f'mhav_announcement_{item.pk}') != str(int(item.updated_at.timestamp()))]
    return {'mhav_announcements': unread}
