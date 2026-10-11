from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import ProfileForm, RegistrationForm
from .models import MemberProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    profile, _ = MemberProfile.objects.get_or_create(user=request.user)
    return render(request, "accounts/dashboard.html", {"profile": profile})


@login_required
def profile_edit(request):
    profile, _ = MemberProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("accounts:dashboard")
    return render(request, "accounts/profile.html", {"form": form})


# MHAV beheer: never expose Django's admin interface to normal club managers.
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .forms import AccountAccessForm
from .roles import ROLE_LABELS


def _is_superuser(user):
    return user.is_authenticated and user.is_active and user.is_superuser


@login_required
def beheer(request):
    if not (request.user.is_superuser or request.user.has_perm('website.change_sectionpagecontent') or request.user.has_perm('website.change_homepagecontent')):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, 'accounts/beheer.html', {
        'user_count': get_user_model().objects.count(),
        'pending_count': MemberProfile.objects.filter(is_approved=False).count(),
    })


@user_passes_test(_is_superuser, login_url='accounts:login')
def beheer_users(request):
    query = request.GET.get('q', '').strip()[:100]
    users = get_user_model().objects.select_related('member_profile').prefetch_related('groups').order_by('-date_joined')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
    return render(request, 'accounts/beheer_users.html', {'users': users[:200], 'query': query})


@user_passes_test(_is_superuser, login_url='accounts:login')
def beheer_user_edit(request, user_id):
    target = get_object_or_404(get_user_model(), pk=user_id)
    if target.is_superuser:
        messages.warning(request, 'Superuser-rechten kunnen hier niet worden aangepast.')
        return redirect('accounts:beheer_users')
    form = AccountAccessForm(request.POST or None, user=target)
    if request.method == 'POST' and form.is_valid():
        if target.pk == request.user.pk and not form.cleaned_data['is_active']:
            form.add_error('is_active', 'Je kunt je eigen account niet uitschakelen.')
        elif get_user_model().objects.exclude(pk=target.pk).filter(email__iexact=form.cleaned_data['email']).exists():
            form.add_error('email', 'Dit e-mailadres is al in gebruik.')
        else:
            with transaction.atomic():
                target.first_name = form.cleaned_data['first_name']
                target.last_name = form.cleaned_data['last_name']
                target.email = form.cleaned_data['email']
                target.is_active = form.cleaned_data['is_active']
                target.save(update_fields=['first_name', 'last_name', 'email', 'is_active'])
                profile, _ = MemberProfile.objects.get_or_create(user=target)
                profile.is_approved = form.cleaned_data['is_approved']
                profile.save(update_fields=['is_approved'])
                names = [name for field, name in (
                    ('role_member', 'MHAV - Lid'), ('role_trainer', 'MHAV - Trainer'),
                    ('role_editor', 'MHAV - Websitebeheer')) if form.cleaned_data[field]]
                # Replace only MHAV roles, preserving any unrelated groups.
                old_roles = Group.objects.filter(name__in=ROLE_LABELS)
                target.groups.remove(*old_roles)
                target.groups.add(*Group.objects.filter(name__in=names))
            messages.success(request, 'Gebruiker bijgewerkt.')
            return redirect('accounts:beheer_users')
    return render(request, 'accounts/beheer_user_edit.html', {'form': form, 'target': target})
