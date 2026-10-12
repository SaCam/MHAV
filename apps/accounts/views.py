from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import ProfileForm, RegistrationForm, MemberDetailsForm
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
    is_complete = all([request.user.first_name, request.user.last_name, request.user.email,
                       profile.phone, profile.street, profile.house_number, profile.postal_code, profile.city])
    from apps.planning.models import Season, TrainerSeasonAvailability

    trainer_role = request.user.is_superuser or request.user.groups.filter(
        name="MHAV - Trainer"
    ).exists()
    upcoming_seasons = []
    if trainer_role:
        seasons = Season.objects.filter(status=Season.Status.DRAFT).order_by("starts_on")
        responses = {
            response.season_id: response
            for response in TrainerSeasonAvailability.objects.filter(trainer=request.user)
        }
        upcoming_seasons = [(season, responses.get(season.pk)) for season in seasons]

    return render(request, "accounts/dashboard.html", {
        "profile": profile, "is_member": request.user.groups.filter(name='MHAV - Lid').exists(),
        "profile_complete": is_complete,
        "is_trainer": trainer_role,
        "trainer_seasons": upcoming_seasons,
    })


@login_required
def profile_edit(request):
    profile, _ = MemberProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        from django.contrib import messages
        messages.success(request, "Je profiel is opgeslagen.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/profile.html", {"form": form})


# MHAV beheer: never expose Django's admin interface to normal club managers.
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .forms import AccountAccessForm
from .roles import ROLE_LABELS


def _is_account_admin(user):
    return (user.is_authenticated and user.is_active and
            (user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists()))


@login_required
def beheer(request):
    if not (_is_account_admin(request.user) or request.user.has_perm('website.change_sectionpagecontent') or request.user.has_perm('website.change_homepagecontent')):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, 'accounts/beheer.html', {
        'user_count': get_user_model().objects.count(),
        'member_count': get_user_model().objects.filter(groups__name='MHAV - Lid').count(),
        'can_manage_users': _is_account_admin(request.user),
    })


@user_passes_test(_is_account_admin, login_url='accounts:login')
def beheer_users(request):
    query = request.GET.get('q', '').strip()[:100]
    role = request.GET.get('role', 'all')
    status = request.GET.get('status', 'all')
    if role not in ('all', 'member', 'trainer', 'member_trainer', 'no_role'):
        role = 'all'
    if status not in ('all', 'active', 'inactive'):
        status = 'all'

    User = get_user_model()
    membership = User.groups.through.objects.filter(user_id=OuterRef('pk'))
    users = User.objects.order_by('-date_joined', '-pk').annotate(
        is_mhav_member=Exists(membership.filter(group__name='MHAV - Lid')),
        is_mhav_trainer=Exists(membership.filter(group__name='MHAV - Trainer')),
    )
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) |
            Q(last_name__icontains=query) | Q(email__icontains=query)
        )
    if role == 'member':
        users = users.filter(is_mhav_member=True)
    elif role == 'trainer':
        users = users.filter(is_mhav_trainer=True)
    elif role == 'member_trainer':
        users = users.filter(is_mhav_member=True, is_mhav_trainer=True)
    elif role == 'no_role':
        users = users.filter(is_mhav_member=False, is_mhav_trainer=False)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)

    page = Paginator(users, 25).get_page(request.GET.get('page'))
    return render(request, 'accounts/beheer_users.html', {
        'users': page, 'page_obj': page, 'query': query, 'role': role, 'status': status,
        'total_results': page.paginator.count,
    })


@user_passes_test(_is_account_admin, login_url='accounts:login')
def beheer_user_edit(request, user_id):
    target = get_object_or_404(get_user_model(), pk=user_id)
    if target.is_superuser:
        messages.warning(request, 'Superuser-rechten kunnen hier niet worden aangepast.')
        return redirect('accounts:beheer_users')
    profile, _ = MemberProfile.objects.get_or_create(user=target)
    form = AccountAccessForm(request.POST or None, user=target)
    details_form = MemberDetailsForm(request.POST or None, instance=profile, prefix='details')
    if request.method == 'POST' and form.is_valid() and details_form.is_valid():
        if target.pk == request.user.pk and not form.cleaned_data['is_active']:
            form.add_error('is_active', 'Je kunt je eigen account niet uitschakelen.')
        elif target.pk == request.user.pk and not form.cleaned_data['role_admin'] and not request.user.is_superuser:
            form.add_error('role_admin', 'Je kunt je eigen administratorrechten niet verwijderen.')
        elif get_user_model().objects.exclude(pk=target.pk).filter(email__iexact=form.cleaned_data['email']).exists():
            form.add_error('email', 'Dit e-mailadres is al in gebruik.')
        else:
            with transaction.atomic():
                target.first_name = form.cleaned_data['first_name']
                target.last_name = form.cleaned_data['last_name']
                target.email = form.cleaned_data['email']
                target.is_active = form.cleaned_data['is_active']
                target.save(update_fields=['first_name', 'last_name', 'email', 'is_active'])
                details_form.save()
                names = [name for field, name in (
                    ('role_member', 'MHAV - Lid'), ('role_trainer', 'MHAV - Trainer'),
                    ('role_editor', 'MHAV - Websitebeheer'), ('role_admin', 'MHAV - Administrator')) if form.cleaned_data[field]]
                # Replace only MHAV roles, preserving any unrelated groups.
                old_roles = Group.objects.filter(name__in=ROLE_LABELS)
                target.groups.remove(*old_roles)
                target.groups.add(*Group.objects.filter(name__in=names))
            messages.success(request, 'Gebruiker bijgewerkt.')
            return redirect('accounts:beheer_users')
    return render(request, 'accounts/beheer_user_edit.html', {'form': form, 'details_form': details_form, 'target': target, 'target_is_trainer': target.groups.filter(name='MHAV - Trainer').exists()})


@login_required
def trainer_profile_edit(request):
    from django.core.exceptions import PermissionDenied
    from apps.website.models import Instructor
    from .trainer_forms import TrainerProfileForm
    if not request.user.is_active or not (request.user.is_superuser or request.user.groups.filter(name='MHAV - Trainer').exists()):
        raise PermissionDenied
    profile, _ = Instructor.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.get_full_name().strip() or request.user.email or request.user.username,
                  'is_visible': False},
    )
    form = TrainerProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Je trainersprofiel is opgeslagen.')
        return redirect('accounts:trainer_profile')
    return render(request, 'accounts/trainer_profile.html', {'form': form, 'trainer_profile': profile})


@user_passes_test(_is_account_admin, login_url='accounts:login')
def beheer_trainer_profile(request, user_id):
    from django.core.exceptions import PermissionDenied
    from apps.website.models import Instructor
    from .trainer_forms import TrainerProfileForm, TrainerVisibilityForm
    target = get_object_or_404(get_user_model(), pk=user_id)
    if not target.groups.filter(name='MHAV - Trainer').exists():
        raise PermissionDenied
    profile, _ = Instructor.objects.get_or_create(
        user=target,
        defaults={'name': target.get_full_name().strip() or target.email or target.username, 'is_visible': False},
    )
    form = TrainerProfileForm(request.POST or None, request.FILES or None, instance=profile)
    visibility_form = TrainerVisibilityForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid() and visibility_form.is_valid():
        form.save()
        visibility_form.save()
        messages.success(request, 'Trainersprofiel bijgewerkt.')
        return redirect('accounts:beheer_user_edit', user_id=target.pk)
    return render(request, 'accounts/trainer_profile.html', {
        'form': form, 'visibility_form': visibility_form, 'trainer_profile': profile, 'target': target,
    })
