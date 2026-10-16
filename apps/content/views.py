from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import NewsSubmissionForm
from .models import NewsPost


def news_list(request):
    posts = NewsPost.public().order_by("-published_at", "-created_at")
    return render(request, "content/news_list.html", {"posts": posts})


def news_detail(request, slug):
    post = get_object_or_404(NewsPost.public(), slug=slug)
    return render(request, "content/news_detail.html", {"post": post})


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def submit_news(request):
    if request.method == "POST":
        form = NewsSubmissionForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.status = NewsPost.Status.REVIEW
            post.published_at = None
            post.save()
            return redirect("content:submitted")
    else:
        form = NewsSubmissionForm()
    return render(request, "content/submit_news.html", {"form": form})


@login_required(login_url="login")
def submitted(request):
    return render(request, "content/submitted.html")


from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Announcement
from .announcement_forms import AnnouncementForm


def _can_manage_announcements(user):
    return user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists())

@login_required
@require_http_methods(['GET'])
def manage_announcements(request):
    if not _can_manage_announcements(request.user):
        raise PermissionDenied
    now = timezone.now()
    announcements = list(Announcement.objects.all())
    for item in announcements:
        if not item.is_published:
            item.visibility_status = 'Concept'
        elif item.published_at > now:
            item.visibility_status = 'Gepland'
        elif item.expires_at is not None and item.expires_at <= now:
            item.visibility_status = 'Verlopen'
        else:
            item.visibility_status = 'Actief'
    return render(request, 'content/announcements_manage.html', {'announcements': announcements})

@login_required
@require_http_methods(['GET', 'POST'])
def edit_announcement(request, pk=None):
    if not _can_manage_announcements(request.user):
        raise PermissionDenied
    announcement = get_object_or_404(Announcement, pk=pk) if pk else None
    form = AnnouncementForm(request.POST or None, instance=announcement)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Mededeling opgeslagen.')
        return redirect('content:announcements_manage')
    return render(request, 'content/announcement_edit.html', {'form':form, 'announcement':announcement})

@require_POST
def announcement_read(request, pk):
    now = timezone.now()
    from django.db.models import Q
    item = get_object_or_404(Announcement.objects.filter(is_published=True, published_at__lte=now).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)), pk=pk)
    target = request.POST.get('next', '/')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = '/'
    response = redirect(target)
    response.set_cookie(f'mhav_announcement_{item.pk}', str(int(item.updated_at.timestamp())), max_age=60*60*24*90, samesite='Lax', secure=request.is_secure(), httponly=True)
    return response
