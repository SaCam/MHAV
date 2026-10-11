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
