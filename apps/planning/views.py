from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from datetime import date
from django.core.exceptions import ValidationError
from .models import Season, Dog, Combination, TrainingGroup, Enrollment, TrainerSeasonAvailability, LessonInstructorOverride
from .forms import SeasonForm, DogForm, CombinationForm, TrainingGroupForm, EnrollmentForm, TrainerAvailabilityForm

def is_planner(user):
    return user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists())

@user_passes_test(is_planner, login_url='accounts:login')
def overview(request):
    seasons=Season.objects.annotate(group_count=Count('groups',distinct=True)).all()
    return render(request,'planning/overview.html',{'seasons':seasons,'dogs':Dog.objects.count(),'combinations':Combination.objects.count()})

@user_passes_test(is_planner, login_url='accounts:login')
def season_detail(request, pk):
    season=get_object_or_404(Season,pk=pk)
    groups=TrainingGroup.objects.filter(season=season).select_related('trainer').annotate(placed_count=Count('enrollments',filter=Q(enrollments__status='placed')))
    responses = list(season.trainer_availabilities.select_related('trainer').all())
    for response in responses:
        response.date_cells = [
            (day, response.status_for_date(day))
            for day in season.lesson_dates
        ]
    return render(request, 'planning/season_detail.html', {
        'season': season,
        'groups': groups,
        'availability_responses': responses,
        'response_count': len(responses),
        'available_count': sum(r.response == TrainerSeasonAvailability.Response.ALL for r in responses),
        'partial_count': sum(r.response == TrainerSeasonAvailability.Response.PARTIAL for r in responses),
    })

@user_passes_test(is_planner, login_url='accounts:login')
def group_detail(request,pk):
    group=get_object_or_404(TrainingGroup.objects.select_related('season','trainer'),pk=pk)
    enrollments=group.enrollments.select_related('combination__handler','combination__dog').all()
    response = TrainerSeasonAvailability.objects.filter(season=group.season, trainer=group.trainer).first() if group.trainer_id else None
    overrides = {item.lesson_date: item for item in group.instructor_overrides.select_related('trainer')}
    lesson_rows = []
    for day in group.scheduled_dates:
        state = response.status_for_date(day) if response else 'unset'
        replacement = overrides.get(day)
        lesson_rows.append({'date': day, 'state': state, 'replacement': replacement,
                            'covered': bool(replacement and replacement.offline_confirmed) or (not replacement and state == 'yes')})
    trainer_choices = get_user_model().objects.filter(is_active=True, groups__name='MHAV - Trainer').distinct().order_by('last_name', 'first_name')
    return render(request,'planning/group_detail.html',{
        'group':group,'enrollments':enrollments,'placed_count':enrollments.filter(status='placed').count(),
        'lesson_rows':lesson_rows,'covered_count':sum(row['covered'] for row in lesson_rows),
        'trainer_choices':trainer_choices,
    })


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def lesson_instructor_override(request, pk, lesson_date):
    group = get_object_or_404(TrainingGroup, pk=pk)
    if group.execution_status != 'planned':
        messages.error(request, 'Een gestarte of afgesloten lesgroep kan niet via de planning worden gewijzigd.')
        return redirect('planning:group_detail', pk=pk)
    try:
        day = date.fromisoformat(lesson_date)
    except ValueError:
        raise Http404
    if day.isoformat() not in group.lesson_dates_selected:
        raise Http404
    trainer_id = request.POST.get('trainer', '').strip()
    if not trainer_id:
        group.instructor_overrides.filter(lesson_date=day).delete()
        messages.success(request, 'Vervangende instructeur verwijderd.')
    else:
        trainer = get_user_model().objects.filter(
            pk=trainer_id, is_active=True, groups__name='MHAV - Trainer'
        ).first() if trainer_id.isdigit() else None
        if trainer is None:
            messages.error(request, 'Selecteer een geldige actieve instructeur.')
        elif trainer.pk == group.trainer_id:
            messages.error(request, 'De hoofdinstructeur is al toegewezen aan deze les.')
        else:
            confirmed = request.POST.get('offline_confirmed') == 'on'
            item, created = LessonInstructorOverride.objects.get_or_create(
                group=group, lesson_date=day,
                defaults={'trainer': trainer, 'offline_confirmed': confirmed},
            )
            if not created:
                # Changing the replacement resets confirmation unless explicitly reconfirmed.
                item.trainer = trainer
                item.offline_confirmed = confirmed
                item.save(update_fields=['trainer', 'offline_confirmed'])
            messages.success(request, 'Vervangende instructeur opgeslagen.')
    return redirect('planning:group_detail', pk=group.pk)

@user_passes_test(is_planner, login_url='accounts:login')
def records(request,kind):
    config={'dogs':(Dog,'Honden'),'combinations':(Combination,'Combinaties'),'enrollments':(Enrollment,'Inschrijvingen')}
    if kind not in config: raise Http404
    model,title=config[kind]
    queryset=model.objects.all()
    if kind=='combinations': queryset=queryset.select_related('handler','dog')
    if kind=='enrollments': queryset=queryset.select_related('group','combination__handler','combination__dog')
    return render(request,'planning/records.html',{'records':queryset[:250],'kind':kind,'heading':title,'total':queryset.count()})

@user_passes_test(is_planner, login_url='accounts:login')
def edit(request,kind,pk=None):
    config={'seasons':(Season,SeasonForm,'Seizoen'),'groups':(TrainingGroup,TrainingGroupForm,'Lesgroep'),'dogs':(Dog,DogForm,'Hond'),'combinations':(Combination,CombinationForm,'Combinatie'),'enrollments':(Enrollment,EnrollmentForm,'Inschrijving')}
    if kind not in config: raise Http404
    model,form_type,title=config[kind]
    instance=get_object_or_404(model,pk=pk) if pk else None
    if kind == 'groups':
        if instance:
            return redirect('planning:group_edit', pk=instance.pk)
        season_id = request.GET.get('season')
        if season_id and season_id.isdigit():
            return redirect('planning:group_new', season_pk=int(season_id))
        messages.info(request, 'Open eerst een seizoen om een lesgroep toe te voegen.')
        return redirect('planning:overview')
    if kind == 'enrollments' and request.method == 'POST':
        target_id = request.POST.get('group') or (instance.group_id if instance else None)
        if target_id and TrainingGroup.objects.filter(pk=target_id).exclude(execution_status='planned').exists():
            messages.error(request, 'Inschrijvingen van gestarte of afgesloten lesgroepen zijn beschermd.')
            return redirect('planning:records', kind='enrollments')
        if instance and instance.group.execution_status != 'planned':
            messages.error(request, 'Deze inschrijving is vergrendeld door cursusuitvoering.')
            return redirect('planning:records', kind='enrollments')
    form=form_type(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        record=form.save(commit=False)
        try:
            record.full_clean()
        except ValidationError as error:
            for field, errors in error.message_dict.items():
                for msg in errors: form.add_error(field if field in form.fields else None,msg)
        else:
            record.save()
            messages.success(request,f'{title} opgeslagen.')
            if kind=='seasons': return redirect('planning:season_detail',pk=record.pk)
            if kind=='groups': return redirect('planning:group_detail',pk=record.pk)
            if kind=='enrollments': return redirect('planning:group_detail',pk=record.group_id)
            return redirect('planning:records',kind=kind)
    return render(request,'planning/edit.html',{'form':form,'heading':title,'editing':bool(pk),'kind':kind})

def _group_coverage(season, selected, trainer_id):
    response = TrainerSeasonAvailability.objects.filter(
        season=season, trainer_id=trainer_id
    ).first() if trainer_id else None
    rows = []
    for day in season.lesson_dates:
        key = day.isoformat()
        if key not in selected:
            continue
        state = response.status_for_date(day) if response else 'unset'
        rows.append({'date': day, 'state': state})
    return rows


@user_passes_test(is_planner, login_url='accounts:login')
def group_manage(request, season_pk=None, pk=None):
    group = get_object_or_404(
        TrainingGroup.objects.select_related('season'), pk=pk
    ) if pk else None
    season = group.season if group else get_object_or_404(Season, pk=season_pk)
    if group and group.execution_status != 'planned':
        messages.warning(request, 'Deze lesgroep is gestart of afgesloten en kan niet meer in de planning worden gewijzigd.')
        return redirect('planning:group_detail', pk=group.pk)
    if season.lesson_day != 'sat':
        messages.error(request, 'Stel de lesdag van het seizoen eerst in op zaterdag.')
        return redirect('planning:season_detail', pk=season.pk)
    form = TrainingGroupForm(request.POST or None, instance=group, season=season)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        try:
            record.full_clean()
        except ValidationError as error:
            if hasattr(error, 'message_dict'):
                for field, errors in error.message_dict.items():
                    for message in errors:
                        form.add_error(field if field in form.fields else None, message)
            else:
                form.add_error(None, error)
        else:
            record.save()
            messages.success(request, 'Lesgroep opgeslagen.')
            return redirect('planning:group_detail', pk=record.pk)
    selected = (
        request.POST.getlist('lesson_dates_selected') if request.method == 'POST'
        else (group.lesson_dates_selected if group else [d.isoformat() for d in season.lesson_dates])
    )
    trainer_id = request.POST.get('trainer') if request.method == 'POST' else (group.trainer_id if group else None)
    coverage = _group_coverage(season, selected, trainer_id)
    # The preview can be updated client-side without submitting the form.
    trainer_states = {
        str(response.trainer_id): {
            day.isoformat(): response.status_for_date(day)
            for day in season.lesson_dates
        }
        for response in TrainerSeasonAvailability.objects.filter(season=season)
    }
    return render(request, 'planning/group_manage.html', {
        'season': season, 'group': group, 'form': form,
        'coverage': coverage, 'trainer_states': trainer_states,
    })


@user_passes_test(is_planner, login_url='accounts:login')
def catalogue(request):
    from apps.website.views import _managed_course_queryset, _can_manage_course
    return render(request, 'planning/catalogue.html', {
        'courses': _managed_course_queryset().order_by('menu_order', 'title'),
        'can_add': _can_manage_course(request.user, 'add'),
        'can_change': _can_manage_course(request.user, 'change'),
    })

from django.db import transaction
from django.utils import timezone
from .models import CourseApplication
from .forms import CourseApplicationForm, ApplicationReviewForm


def _offered_times(season_id=None, course_id=None):
    import json
    from .models import SeasonCourseOffering
    open_pairs = {(o.season_id, o.course_id) for o in SeasonCourseOffering.objects.select_related('season', 'course') if o.accepts_applications()}
    if season_id:
        open_pairs = {(s, c) for s, c in open_pairs if str(s) == str(season_id)}
    if course_id:
        open_pairs = {(s, c) for s, c in open_pairs if str(c) == str(course_id)}
    if not open_pairs:
        return []
    groups = TrainingGroup.objects.filter(
        season_id__in={s for s, _ in open_pairs}, course_id__in={c for _, c in open_pairs}
    ).select_related('season').order_by('season__starts_on', 'day', 'starts_at', 'pk')
    return [group for group in groups if (group.season_id, group.course_id) in open_pairs]


def public_application(request, on_behalf=False):
    """Single intake for guests, members, and authorized administrators."""
    if on_behalf and not is_planner(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Alleen beheerders mogen namens iemand aanmelden.')
    initial = {}
    if request.user.is_authenticated and not on_behalf:
        u = request.user
        initial.update(first_name=u.first_name, last_name=u.last_name, email=u.email)
        profile = getattr(u, 'member_profile', None)
        if profile:
            for field in ('phone', 'street', 'house_number', 'postal_code', 'city'):
                initial[field] = getattr(profile, field, '')
    form = CourseApplicationForm(
        request.POST or None,
        initial=initial if request.method != 'POST' else None,
        applicant_user=request.user if request.user.is_authenticated and not on_behalf else None,
    )
    selected_course = request.POST.get('course') if request.method == 'POST' else request.GET.get('course')
    selected_season = request.POST.get('season') if request.method == 'POST' else request.GET.get('season')
    if selected_season and str(selected_season).isdigit() and request.method != 'POST':
        season = form.fields['season'].queryset.filter(pk=int(selected_season)).first()
        if season:
            form.initial['season'] = season.pk
    if selected_course and str(selected_course).isdigit() and request.method != 'POST':
        # Only preselect a published course that is actually offered by this form.
        course = form.fields['course'].queryset.filter(pk=int(selected_course)).first()
        if course:
            form.initial['course'] = course.pk
    groups = _offered_times(selected_season, selected_course) if (selected_season and str(selected_season).isdigit() and selected_course and str(selected_course).isdigit()) else []
    preferences = {}
    preference_error = ''
    if request.method == 'POST' and form.is_valid():
        for group in groups:
            key = f'time_{group.pk}'
            choice = request.POST.get(key, '')
            if choice and choice not in ('ok','preferred','unavailable'):
                preference_error = 'Ongeldige beschikbaarheidskeuze.'
                break
            if choice:
                preferences[str(group.pk)] = choice
        if not preference_error:
            with transaction.atomic():
                application = form.save(commit=False)
                application.requested_season = application.season if application.start_preference == CourseApplication.StartPreference.SPECIFIC else None
                application.privacy_accepted_at = timezone.now()
                application.time_preferences = preferences
                application.submission_source = 'admin' if on_behalf else ('member' if request.user.is_authenticated else 'guest')
                if request.user.is_authenticated:
                    application.submitted_by = request.user
                if request.user.is_authenticated and not on_behalf:
                    application.user = request.user
                if not on_behalf and request.user.is_authenticated:
                    selected_dog = form.cleaned_data.get('existing_dog')
                    if selected_dog:
                        application.dog_profile = selected_dog
                application.save()
                if application.user_id:
                    from apps.accounts.dog_profiles import ensure_application_dog
                    ensure_application_dog(application)
            if not on_behalf:
                request.session['last_course_application_id'] = application.pk
                request.session['mhav_pending_application_id'] = application.pk
            # Email verification is sent on demand; no account is created here.
            if on_behalf:
                messages.success(request, 'De aanmelding is namens de cursist ontvangen.')
                return redirect('planning:application_detail', pk=application.pk)
            return redirect('website:application_thanks')
    import json
    from .models import SeasonCourseOffering
    open_pairs = [[o.season_id, o.course_id] for o in SeasonCourseOffering.objects.select_related('season', 'course') if o.accepts_applications()]
    visible_groups = _offered_times(selected_season, selected_course) if selected_season and selected_course else []
    return render(request, 'planning/application_form.html', {'form': form, 'groups': visible_groups,
        'open_pairs_json': json.dumps(open_pairs),
        'posted_preferences': request.POST if request.method == 'POST' else {},
        'preference_error': preference_error, 'on_behalf': on_behalf})


def application_thanks(request):
    pk = request.session.get('last_course_application_id')
    application = CourseApplication.objects.filter(pk=pk).first() if pk else None
    from django.contrib.auth import get_user_model
    known_email = bool(application and get_user_model().objects.filter(email__iexact=application.email).exists())
    return render(request, 'planning/application_thanks.html', {
        'application': application, 'known_email': known_email,
        'owns_application': bool(application and request.user.is_authenticated and application.user_id == request.user.pk),
    })


def _claim_signer():
    from django.core import signing
    return signing.TimestampSigner(salt='mhav-course-account-claim-v1')


def request_account_invite(request):
    """Email a verification link to the address on this session's application."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    from django.core import signing
    from django.contrib.auth import get_user_model
    if request.method != 'POST':
        return redirect('website:application_thanks')
    pk = request.session.get('last_course_application_id')
    application = CourseApplication.objects.filter(pk=pk).first() if pk else None
    if application and not request.user.is_authenticated:
        token = _claim_signer().sign(str(application.pk))
        url = request.build_absolute_uri(reverse('website:application_account_claim', args=[token]))
        try:
            send_mail('MHAV - Bevestig je e-mailadres',
                'Je hebt aangegeven een MHAV-account te willen aanmaken. Open deze link binnen 24 uur:\n' + url +
                '\n\nHeb je dit niet aangevraagd? Negeer dit bericht.',
                getattr(settings,'DEFAULT_FROM_EMAIL','noreply@mhav.nl'), [application.email], fail_silently=False)
            messages.success(request, 'Controleer je e-mail voor de verificatielink.')
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Unable to send MHAV account verification email')
            messages.error(request, 'De e-mail kon niet worden verzonden. Probeer het later opnieuw.')
    return redirect('website:application_thanks')


def application_account_claim(request, token):
    """Only possession of a recent emailed link authorizes account creation/linking."""
    from django.core import signing
    from django.contrib.auth import get_user_model, login
    from django.contrib.auth.forms import SetPasswordForm
    from apps.accounts.models import MemberProfile
    from uuid import uuid4
    try:
        pk = int(_claim_signer().unsign(token, max_age=86400))
    except (signing.BadSignature, signing.SignatureExpired, ValueError):
        raise Http404('Deze link is ongeldig of verlopen.')
    application = get_object_or_404(CourseApplication, pk=pk)
    if application.user_id:
        return render(request, 'planning/application_account_claim.html', {'already_linked': True})
    User = get_user_model()
    existing = User.objects.filter(email__iexact=application.email).first()
    if existing:
        # A signed email link proves control of the mailbox, but linking an
        # existing account also requires an authenticated session for that account.
        if request.method == 'POST':
            if not request.user.is_authenticated:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('Log eerst in met je bestaande MHAV-account.')
            if request.user.pk != existing.pk:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('Deze aanmelding hoort bij een ander account.')
            with transaction.atomic():
                locked = CourseApplication.objects.select_for_update().get(pk=pk)
                if locked.user_id and locked.user_id != existing.pk:
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied('Deze aanmelding is al aan een ander account gekoppeld.')
                if not locked.user_id:
                    locked.user = existing
                    locked.save(update_fields=['user'])
            messages.success(request, 'Je cursusaanmelding is gekoppeld aan je MHAV-account.')
            return redirect('accounts:dashboard')
        return render(request, 'planning/application_account_claim.html', {
            'existing': True,
            'matching_account': request.user.is_authenticated and request.user.pk == existing.pk,
            'wrong_account': request.user.is_authenticated and request.user.pk != existing.pk,
            'login_next': request.get_full_path(),
        })
    from django import forms
    class PasswordForm(forms.Form):
        password1 = forms.CharField(label='Wachtwoord', widget=forms.PasswordInput)
        password2 = forms.CharField(label='Herhaal wachtwoord', widget=forms.PasswordInput)
        def clean(self):
            data = super().clean()
            from django.contrib.auth.password_validation import validate_password
            if data.get('password1') and data.get('password2'):
                if data['password1'] != data['password2']:
                    raise forms.ValidationError('Wachtwoorden komen niet overeen.')
                validate_password(data['password1'])
            return data
    form = PasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            application = CourseApplication.objects.select_for_update().get(pk=pk)
            if application.user_id or User.objects.filter(email__iexact=application.email).exists():
                messages.error(request, 'Dit e-mailadres is al gekoppeld aan een account. Log in om verder te gaan.')
                return redirect('accounts:login')
            user = User(username='mhav_'+uuid4().hex[:24], email=application.email,
                first_name=application.first_name, last_name=application.last_name)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            profile, _ = MemberProfile.objects.get_or_create(user=user)
            profile.phone = application.phone
            profile.save(update_fields=['phone'])
            CourseApplication.objects.filter(pk=pk, user__isnull=True).update(user=user)
        login(request, user)
        return redirect('accounts:dashboard')
    return render(request, 'planning/application_account_claim.html', {'form': form})


@user_passes_test(is_planner, login_url='accounts:login')
def application_list(request):
    from apps.website.models import SitePage
    from .models import Enrollment
    from collections import defaultdict

    status = request.GET.get('status', 'open')
    season_filter = request.GET.get('season', '')
    course_filter = request.GET.get('course', '')
    search = request.GET.get('q', '').strip()
    applications = CourseApplication.objects.select_related('course', 'season', 'proposed_group', 'linked_enrollment__group__season', 'linked_enrollment__group__course')
    if status == 'open':
        applications = applications.filter(linked_enrollment__isnull=True).exclude(status__in=[CourseApplication.Status.PROCESSED, CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST])
    elif status == 'draft':
        applications = applications.filter(proposed_group__isnull=False, linked_enrollment__isnull=True)
    elif status == 'unplanned':
        applications = applications.filter(proposed_group__isnull=True, linked_enrollment__isnull=True).exclude(
            status__in=[CourseApplication.Status.PROCESSED, CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST])
    elif status == 'handled':
        applications = applications.filter(status__in=[CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST])
    elif status == 'processed':
        applications = applications.filter(status=CourseApplication.Status.PROCESSED)
    elif status in CourseApplication.Status.values:
        applications = applications.filter(status=status)

    if season_filter == 'open':
        applications = applications.filter(season__isnull=True)
    elif season_filter.isdecimal():
        applications = applications.filter(season_id=int(season_filter))
    if course_filter.isdecimal():
        applications = applications.filter(course_id=int(course_filter))
    if search:
        applications = applications.filter(
            Q(first_name__icontains=search) | Q(middle_name__icontains=search)
            | Q(last_name__icontains=search) | Q(dog_name__icontains=search)
            | Q(email__icontains=search))

    applications = applications.order_by('created_at', 'pk')
    total = applications.count()
    items = list(applications[:250])
    course_ids = {a.course_id for a in items if a.course_id}
    season_ids = {a.season_id for a in items if a.season_id}
    open_course_ids = {a.course_id for a in items if a.season_id is None and a.course_id}
    groups = list(TrainingGroup.objects.filter(course_id__in=course_ids).filter(Q(season_id__in=season_ids) | Q(course_id__in=open_course_ids, season__status__in=[Season.Status.ACTIVE, Season.Status.DRAFT]))
                  .select_related('season').annotate(placed_count=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.PLACED)))) if (season_ids or open_course_ids) else []
    concept_counts = dict(CourseApplication.objects.filter(proposed_group__isnull=False, linked_enrollment__isnull=True).values('proposed_group_id').annotate(total=Count('pk')).values_list('proposed_group_id', 'total'))
    by_pair = defaultdict(list)
    for group in groups:
        by_pair[(group.season_id, group.course_id)].append(group)
    for application in items:
        application.open_application = application.season_id is None
        application.planning_state = ('Verwerkt' if application.linked_enrollment_id else 'Afgehandeld' if application.status in (CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST) else 'Voorlopig gepland' if application.proposed_group_id else 'Te plannen')
        application.group_options = []
        if application.linked_enrollment_id or application.status in (CourseApplication.Status.PROCESSED, CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST):
            continue
        for group in ([g for g in groups if g.course_id == application.course_id and g.season.status in (Season.Status.ACTIVE, Season.Status.DRAFT)] if application.season_id is None else by_pair.get((application.season_id, application.course_id), [])):
            preference = (application.time_preferences or {}).get(str(group.pk), '')
            application.group_options.append({
                'group': group, 'preference': preference,
                'definitive': group.placed_count,
                'concept': concept_counts.get(group.pk, 0),
                'capacity': group.capacity,
                'free': max(0, group.capacity - group.placed_count - concept_counts.get(group.pk, 0)),
                'available': group.execution_status == 'planned' and group.placed_count + concept_counts.get(group.pk, 0) < group.capacity and not group.planning_locked_at,
            })
        application.preferred_available = any(o['preference'] == 'preferred' and o['available'] for o in application.group_options)
        application.has_preference = any(o['preference'] == 'preferred' for o in application.group_options)
    return render(request, 'planning/applications.html', {
        'applications': items, 'total': total,
        'statuses': [('open', 'Openstaande aanmeldingen'), ('unplanned', 'Te plannen'), ('draft', 'Voorlopig gepland'), ('processed', 'Verwerkt'), ('handled', 'Afgehandeld'), ('waitlist', 'Wachtlijst'), ('rejected', 'Niet geplaatst / ingetrokken')],
        'current_status': status, 'current_season': season_filter, 'current_course': course_filter, 'search_query': search,
        'seasons': Season.objects.all().order_by('-starts_on'),
        'courses': SitePage.objects.filter(course_applications__isnull=False).distinct().order_by('title'),
        'action_groups': TrainingGroup.objects.select_related('season').order_by('season__starts_on', 'name'),
        'draft_count': CourseApplication.objects.filter(proposed_group__isnull=False, linked_enrollment__isnull=True).exclude(status__in=[CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST]).count(),
        'season_reviews': _season_application_reviews(),
    })


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_verify_identity(request, pk):
    """Administrator records an independently checked identity before linking an account."""
    from django.db import transaction
    from django.utils import timezone
    from .models import CourseApplication
    from .finalization import resolve_identity

    account_id = request.POST.get('account_id', '').strip()
    method = request.POST.get('verification_method', '').strip()
    reference = request.POST.get('verification_reference', '').strip()
    if method not in ('in_person', 'video_call', 'authenticated_contact') or not reference or len(reference) > 500:
        messages.error(request, 'Kies een verificatiemethode en leg kort vast hoe de identiteit is gecontroleerd.')
        return redirect('planning:application_detail', pk=pk)
    if not account_id.isdecimal():
        messages.error(request, 'Selecteer een geldig MHAV-account.')
        return redirect('planning:application_detail', pk=pk)
    with transaction.atomic():
        app = get_object_or_404(CourseApplication.objects.select_for_update(), pk=pk)
        user = get_user_model().objects.filter(pk=int(account_id), is_active=True).first()
        if not user or app.linked_enrollment_id or app.user_id:
            messages.error(request, 'Aanmelding is al gekoppeld of het account is niet beschikbaar.')
        elif user.email.strip().casefold() != app.email.strip().casefold():
            messages.error(request, 'E-mailadres van aanvraag en account komen niet overeen.')
        elif (user.first_name.strip().casefold() != app.first_name.strip().casefold()
              or user.last_name.strip().casefold() != app.last_name.strip().casefold()):
            messages.error(request, 'Naam van aanvraag en account komen niet overeen. Onderzoek dit eerst.')
        elif get_user_model().objects.filter(email__iexact=app.email).exclude(pk=user.pk).exists():
            messages.error(request, 'Meerdere accounts met dit e-mailadres: eerst handmatig oplossen.')
        elif app.linked_combination_id and app.linked_combination.handler_id != user.pk:
            messages.error(request, 'De gekoppelde geleider-hondcombinatie hoort bij een ander account.')
        elif app.dog_profile_id and not Combination.objects.filter(handler=user, dog_id=app.dog_profile_id).exists():
            messages.error(request, 'Het hondenprofiel hoort niet bij het gekozen account.')
        else:
            app.user = user
            app.identity_verified_by = request.user
            app.identity_verified_at = timezone.now()
            app.identity_verification_method = method
            app.identity_verification_reference = reference
            app.save(update_fields=['user', 'identity_verified_by', 'identity_verified_at',
                                    'identity_verification_method', 'identity_verification_reference', 'updated_at'])
            messages.success(request, 'Accountkoppeling na identiteitscontrole opgeslagen.')
    return redirect('planning:application_detail', pk=pk)


@user_passes_test(is_planner, login_url='accounts:login')
def application_detail(request, pk):
    application = get_object_or_404(CourseApplication.objects.select_related('course','season','user'), pk=pk)
    form = ApplicationReviewForm(request.POST or None, instance=application)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Aanmelding bijgewerkt.')
        return redirect('planning:application_detail', pk=pk)
    from .application_planning import compatible_groups
    groups = TrainingGroup.objects.filter(course=application.course, season__status__in=[Season.Status.DRAFT, Season.Status.ACTIVE], planning_locked_at__isnull=True, execution_status='planned').select_related('season') if application.course_id and application.season_id is None else (TrainingGroup.objects.filter(season=application.season, course=application.course, planning_locked_at__isnull=True, execution_status='planned').select_related('season') if application.season_id and application.course_id else TrainingGroup.objects.none())
    eligible = [g for _, g in compatible_groups(application, groups)]
    preferences = [{'group': g, 'preference': (application.time_preferences or {}).get(str(g.pk), '')} for g in groups.order_by('day', 'starts_at', 'pk')]
    return render(request, 'planning/application_detail.html', {'application':application, 'form':form, 'eligible_groups':eligible, 'time_preference_rows':preferences, 'combinations':Combination.objects.select_related('handler', 'dog').order_by('handler__last_name')[:300]})


def is_trainer(user):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or user.groups.filter(name='MHAV - Trainer').exists()
    )


def trainer_availability_locked(season):
    """Availability is frozen once any group in the season is approved or enrolled."""
    return (season.status != Season.Status.DRAFT or
            TrainingGroup.objects.filter(season=season).filter(
                Q(planning_locked_at__isnull=False) |
                ~Q(execution_status=TrainingGroup.ExecutionStatus.PLANNED) |
                Q(enrollments__status=Enrollment.Status.PLACED)
            ).exists())


@user_passes_test(is_trainer, login_url='accounts:login')
def trainer_seasons(request):
    seasons = [season for season in Season.objects.filter(status=Season.Status.DRAFT).order_by('starts_on') if not trainer_availability_locked(season)]
    responses = {r.season_id: r for r in TrainerSeasonAvailability.objects.filter(trainer=request.user)}
    return render(request, 'planning/trainer_seasons.html', {
        'seasons_with_responses': [(season, responses.get(season.pk)) for season in seasons],
    })


@user_passes_test(is_trainer, login_url='accounts:login')
def trainer_availability(request, pk):
    season = get_object_or_404(Season, pk=pk)
    if trainer_availability_locked(season):
        raise Http404(
            "De beschikbaarheid voor dit seizoen kan niet meer worden aangepast."
        )

    response = TrainerSeasonAvailability.objects.filter(
        season=season, trainer=request.user
    ).first()
    dates = season.lesson_dates
    allowed = {day.isoformat() for day in dates}

    # ModelForm calls model.full_clean() inside is_valid(). The season, trainer
    # and date statuses MUST already be set on its instance at that point.
    # Otherwise a new response fails validation before the save code is reached.
    availability = response or TrainerSeasonAvailability(
        season=season, trainer=request.user
    )
    if request.method == 'POST':
        selected_mode = request.POST.get('response')
        if selected_mode == TrainerSeasonAvailability.Response.PARTIAL:
            submitted = {
                day.isoformat(): request.POST.get(
                    f'date_status_{day.isoformat()}', 'unset'
                )
                for day in dates
            }
        elif selected_mode in (
            TrainerSeasonAvailability.Response.ALL,
            TrainerSeasonAvailability.Response.NONE,
        ):
            state = (
                'yes' if selected_mode == TrainerSeasonAvailability.Response.ALL
                else 'no'
            )
            submitted = {day.isoformat(): state for day in dates}
        else:
            submitted = {}

        # Only valid values are ever passed to the model. An invalid submitted
        # state is reported on the form rather than causing a server error.
        invalid_states = any(
            state not in ('yes', 'no', 'maybe', 'unset')
            for state in submitted.values()
        )
        if not invalid_states:
            availability.date_statuses = submitted
            availability.unavailable_dates = [
                day for day, state in submitted.items() if state == 'no'
            ]

    form = TrainerAvailabilityForm(request.POST or None, instance=availability)
    if request.method == 'POST':
        if invalid_states:
            form.add_error(None, 'Er is een ongeldige keuze voor een lesdag.')
        elif form.is_valid():
            saved = form.save(commit=False)
            saved.season = season
            saved.trainer = request.user
            saved.save()
            messages.success(request, 'Je beschikbaarheid is opgeslagen.')
            return redirect('planning:trainer_seasons')

    mode = (
        request.POST.get('response')
        if request.method == 'POST'
        else (response.response if response else TrainerSeasonAvailability.Response.PARTIAL)
    )
    date_cells = []
    for day in dates:
        key = day.isoformat()
        if request.method == 'POST':
            status = request.POST.get(f'date_status_{key}', 'unset')
        elif response:
            status = response.status_for_date(day)
        else:
            status = 'unset'
        if mode == TrainerSeasonAvailability.Response.ALL:
            status = 'yes'
        elif mode == TrainerSeasonAvailability.Response.NONE:
            status = 'no'
        if status not in ('yes', 'no', 'maybe', 'unset'):
            status = 'unset'
        date_cells.append({'date': day, 'key': key, 'status': status})

    return render(request, 'planning/trainer_availability.html', {
        'season': season,
        'form': form,
        'date_cells': date_cells,
    })


@user_passes_test(is_planner, login_url='accounts:login')
def season_course_offerings(request, pk):
    from .models import SeasonCourseOffering
    from apps.website.models import SitePage
    from apps.website.views import TRAINING_SLUGS
    from django.db import transaction
    season = get_object_or_404(Season, pk=pk)
    courses = SitePage.objects.filter(Q(slug__in=TRAINING_SLUGS) | Q(slug__startswith='cursus-')).exclude(slug='phv-knpv').filter(is_published=True).order_by('title')
    offerings = {o.course_id: o for o in SeasonCourseOffering.objects.filter(season=season).select_related('course')}
    if request.method == 'POST':
        course = get_object_or_404(courses, pk=request.POST.get('course_id'))
        action = request.POST.get('action')
        with transaction.atomic():
            offering, _ = SeasonCourseOffering.objects.select_for_update().get_or_create(season=season, course=course)
            snapshot = offering.planning_snapshot()
            if action == 'approve':
                reason = request.POST.get('override_reason', '').strip()
                override = bool(snapshot['uncovered'])
                if snapshot['issues']:
                    messages.error(request, 'Publicatie geblokkeerd: los eerst de verplichte planningspunten op.')
                elif override and not reason:
                    messages.error(request, 'Vul een reden in voor de ontbrekende instructeursdekking.')
                else:
                    offering.approved = True
                    offering.coverage_override = override
                    offering.override_reason = reason if override else ''
                    offering.approved_by = request.user
                    offering.approved_at = timezone.now()
                    offering.approval_signature = snapshot['signature']
                    offering.save()
                    messages.success(request, 'Cursusplanning goedgekeurd.')
            elif action == 'open':
                if offering.approval_valid(snapshot):
                    offering.registration_open = True
                    offering.save(update_fields=['registration_open'])
                    messages.success(request, 'Inschrijving geopend.')
                else:
                    messages.error(request, 'Goedkeuring ontbreekt of de planning is na goedkeuring gewijzigd.')
            elif action == 'close':
                offering.registration_open = False
                offering.save(update_fields=['registration_open'])
                messages.success(request, 'Inschrijving gesloten.')
            elif action == 'revoke':
                # Published course approval is a prerequisite for registration. Never
                # revoke it after the group has acquired definitive enrollments.
                definitive = Enrollment.objects.filter(
                    group__season=season, group__course=course,
                    status=Enrollment.Status.PLACED,
                ).exists()
                if definitive:
                    messages.error(request, 'Goedkeuring intrekken is niet toegestaan: deze cursus heeft definitieve inschrijvingen. Sluit zo nodig alleen de inschrijving; bestaande deelnemers blijven behouden.')
                else:
                    offering.approved = False
                    offering.registration_open = False
                    offering.save(update_fields=['approved', 'registration_open'])
                    messages.success(request, 'Goedkeuring ingetrokken. Bestaande conceptaanmeldingen blijven behouden.')
        return redirect('planning:season_course_offerings', pk=pk)
    rows = []
    for course in courses:
        offering = offerings.get(course.pk) or SeasonCourseOffering(season=season, course=course)
        snapshot = offering.planning_snapshot()
        rows.append({'course': course, 'offering': offering, 'snapshot': snapshot,
                     'valid': offering.approval_valid(snapshot), 'open': offering.accepts_applications()})
    return render(request, 'planning/season_course_offerings.html', {'season': season, 'rows': rows})


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_plan_action(request):
    """Clear drafts or approve/lock a whole season or one lesson group."""
    from django.db import transaction
    from django.utils import timezone
    from django.urls import reverse
    from urllib.parse import urlencode
    action = request.POST.get('action')
    season_raw = request.POST.get('season', '')
    group_raw = request.POST.get('group', '')
    if action not in ('clear', 'approve', 'unlock', 'finalize') or not season_raw.isdecimal():
        messages.error(request, 'Kies een seizoen en een geldige actie.')
        return redirect('planning:application_plan_review')
    season = get_object_or_404(Season, pk=int(season_raw))
    if group_raw and not group_raw.isdecimal():
        messages.error(request, 'Ongeldige lesgroep.')
        return redirect('planning:application_plan_review')
    group_id = int(group_raw) if group_raw else None
    destination = reverse('planning:application_plan_review') + '?' + urlencode({'season': season.pk})
    with transaction.atomic():
        groups_qs = TrainingGroup.objects.select_for_update().filter(season=season).order_by('pk')
        if group_id is not None:
            groups_qs = groups_qs.filter(pk=group_id)
        groups = list(groups_qs)
        if not groups:
            messages.error(request, 'Geen lesgroepen gevonden binnen de gekozen selectie.')
            return redirect(destination)
        ids = [g.pk for g in groups]
        if any(g.execution_status != 'planned' for g in groups):
            messages.error(request, 'De selectie bevat gestarte of afgesloten lesgroepen. Gebruik Cursusuitvoering; de planning is niet gewijzigd.')
            return redirect(destination)
        if action == 'unlock':
            if not request.user.is_superuser and not request.user.has_perm('planning.change_traininggroup'):
                messages.error(request, 'Alleen bevoegde beheerders mogen een planning ontgrendelen.')
                return redirect(destination)
            # A finalized group cannot be reopened via the concept-planning workflow.
            finalized_ids = list(Enrollment.objects.filter(group_id__in=ids, status=Enrollment.Status.PLACED).values_list('group_id', flat=True).distinct())
            if finalized_ids:
                messages.error(request, 'Ontgrendelen geweigerd: deze selectie bevat lesgroepen met definitieve inschrijvingen. Wijzig deze via de inschrijvingsadministratie.')
                return redirect(destination)
            changed = TrainingGroup.objects.filter(pk__in=ids, planning_locked_at__isnull=False).update(planning_locked_at=None, planning_locked_by=None)
            messages.success(request, f'{changed} lesgroep(en) ontgrendeld. Definitieve inschrijvingen blijven behouden.')
        elif action == 'finalize':
            from .finalization import inspect_application, resolve_identity
            selected = list(CourseApplication.objects.select_for_update(of=('self',)).filter(proposed_group_id__in=ids, linked_enrollment__isnull=True).select_related('linked_combination__dog', 'proposed_group').order_by('created_at','pk'))
            if any(not g.planning_locked_at for g in groups if any(a.proposed_group_id == g.pk for a in selected)):
                messages.error(request, 'Keur de conceptplanning eerst goed voordat je inschrijvingen definitief verwerkt.')
                return redirect(destination)
            preview = []
            for app in selected:
                problem = inspect_application(app, app.proposed_group)
                preview.append({'app': app, 'problem': problem})
            if request.POST.get('confirm_finalization') != 'yes':
                return render(request, 'planning/finalization_preview.html', {
                    'season':season, 'scope_group':groups[0] if group_id else None,
                    'preview':preview, 'ready':sum(not row['problem'] for row in preview),
                    'blocked':sum(bool(row['problem']) for row in preview),
                })
            completed = 0
            problems = []
            from django.db import transaction as db_transaction
            for row in preview:
                app = row['app']
                if row['problem']:
                    problems.append(f'#{app.pk}: {row["problem"]}')
                    continue
                try:
                    with db_transaction.atomic():
                        user,dog,combo,problem=resolve_identity(app,create=True)
                        if problem:raise ValueError(problem)
                        g=app.proposed_group
                        used=Enrollment.objects.filter(group=g,status=Enrollment.Status.PLACED).count()
                        over=used>=g.capacity
                        if over and not app.capacity_override_by_id:
                            raise ValueError('Capaciteit bereikt zonder toestemming')
                        if Enrollment.objects.filter(group=g,combination=combo).exists():
                            raise ValueError('Combinatie is al ingeschreven in deze groep')
                        enrollment=Enrollment(group=g,combination=combo,status=Enrollment.Status.PLACED,
                            capacity_override_by_id=app.capacity_override_by_id if over else None,
                            capacity_override_at=app.capacity_override_at if over else None)
                        enrollment.full_clean()
                        enrollment.save()
                        app.user=user
                        app.linked_combination=combo
                        app.linked_enrollment=enrollment
                        app.proposed_group=None
                        app.status=CourseApplication.Status.PROCESSED
                        app.save(update_fields=['user','linked_combination','linked_enrollment','proposed_group','status','updated_at'])
                    completed+=1
                except (ValueError, ValidationError) as exc:
                    problems.append(f'#{app.pk}: {exc}')
            messages.success(request, f'{completed} aanvraag/aanvragen definitief verwerkt. Er zijn geen e-mails verzonden.')
            if problems:
                messages.warning(request, f'{len(problems)} niet verwerkt: ' + '; '.join(problems[:12]))
        elif action == 'clear':
            if any(g.planning_locked_at for g in groups):
                messages.error(request, 'Deze selectie bevat goedgekeurde lesgroepen. Ontgrendel deze eerst; er is niets gewist.')
                return redirect(destination)
            # Only drafts, never confirmed enrollments or processed applications.
            drafts = CourseApplication.objects.select_for_update().filter(proposed_group_id__in=ids, linked_enrollment__isnull=True)
            clear_mode = request.POST.get('clear_mode', 'automatic')
            if clear_mode not in ('automatic', 'all'):
                messages.error(request, 'Ongeldige wisoptie.')
                return redirect(destination)
            if clear_mode == 'automatic':
                drafts = drafts.filter(placement_source='automatic')
            cleared = drafts.update(proposed_group=None, placement_source='legacy', capacity_override_by=None, capacity_override_at=None, updated_at=timezone.now())
            messages.success(request, f'{cleared} conceptplaatsingen gewist ({"alleen automatisch" if clear_mode == "automatic" else "alle conceptplaatsingen"}). Definitieve inschrijvingen blijven behouden.')
        else:
            if season.status == Season.Status.CLOSED:
                messages.error(request, 'Een afgesloten seizoen kan niet worden goedgekeurd.')
                return redirect(destination)
            if any(g.planning_locked_at for g in groups):
                messages.error(request, 'Een of meer lesgroepen zijn al goedgekeurd. Er is niets gewijzigd.')
                return redirect(destination)
            # Automatic planning enforces capacity. Administrators may explicitly
            # authorize an over-capacity concept allocation during approval.
            for g in groups:
                draft_apps = list(CourseApplication.objects.select_for_update().filter(
                    proposed_group=g, linked_enrollment__isnull=True
                ).order_by('created_at', 'pk'))
                occupied = Enrollment.objects.filter(
                    group=g, status=Enrollment.Status.PLACED
                ).count()
                excess = max(0, occupied + len(draft_apps) - g.capacity)
                if excess and request.POST.get('allow_over_capacity') != 'yes':
                    messages.error(request, (
                        f'{g.name}: {occupied + len(draft_apps)}/{g.capacity} plaatsen. '
                        'Vink ‘Capaciteitsoverschrijding toestaan’ aan en keur opnieuw goed.'
                    ))
                    return redirect(destination)
                # Mark only the positions exceeding capacity as approved exceptions.
                # Preserve existing overrides already granted during manual placement.
                available = max(0, g.capacity - occupied)
                for app in draft_apps[available:]:
                    if not app.capacity_override_by_id:
                        app.capacity_override_by = request.user
                        app.capacity_override_at = timezone.now()
                        app.save(update_fields=['capacity_override_by', 'capacity_override_at', 'updated_at'])
            # Only approval claims an open application for this season. Draft
            # generation/clearing never mutates the applicant's season.
            open_approved = CourseApplication.objects.filter(
                proposed_group_id__in=ids, season__isnull=True,
                linked_enrollment__isnull=True,
            ).update(season=season, updated_at=timezone.now())
            now = timezone.now()
            TrainingGroup.objects.filter(pk__in=ids).update(planning_locked_at=now, planning_locked_by=request.user)
            messages.success(request, f'{len(groups)} lesgroep(en) goedgekeurd en vergrendeld; {open_approved} open aanmelding(en) aan dit seizoen gekoppeld. Inschrijvingen zijn nog niet definitief verwerkt.')
    return redirect(destination)


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_auto_plan(request):
    from django.db import transaction
    from .application_planning import generate_proposals
    season_raw = request.POST.get('season', '').strip()
    course_raw = request.POST.get('course', '').strip()
    if not season_raw.isdecimal():
        messages.error(request, 'Selecteer eerst een seizoen voor automatisch plannen.')
        return redirect('planning:application_plan_review')
    season = get_object_or_404(Season, pk=int(season_raw))
    course_id = None
    if course_raw:
        if not course_raw.isdecimal():
            messages.error(request, 'Ongeldige cursusselectie.')
            return redirect('planning:application_plan_review')
        from apps.website.models import SitePage
        course_id = get_object_or_404(SitePage, pk=int(course_raw)).pk
    with transaction.atomic():
        placed, unplaced = generate_proposals(season_id=season.pk, course_id=course_id)
    messages.success(request, f'{placed} voorlopige plaatsingen gemaakt; {unplaced} aanvragen zonder passend lesmoment. Open aanmeldingen zijn voorstellen zonder bevestigde tijdsvoorkeur: controleer deze vóór goedkeuring.')
    from django.urls import reverse
    from urllib.parse import urlencode
    query = {'season': season.pk}
    if course_id is not None:
        query['course'] = course_id
    return redirect(reverse('planning:application_plan_review') + '?' + urlencode(query))


@user_passes_test(is_planner, login_url='accounts:login')
def application_plan_review(request):
    from .planning_insights import build_insights
    from apps.website.models import SitePage
    season_filter = request.GET.get('season', '')
    course_filter = request.GET.get('course', '')
    outcome_filter = request.GET.get('outcome', '')
    phase = request.GET.get('phase', 'planning')
    if phase not in ('planning', 'active', 'history', 'all'):
        phase = 'planning'
    season_id = int(season_filter) if season_filter.isdecimal() else None
    course_id = int(course_filter) if course_filter.isdecimal() else None
    insights = build_insights(season_id=season_id, course_id=course_id, phase=phase)
    # Build a nested season → course → group → participant view, retaining FIFO order.
    from collections import defaultdict
    tree = {}
    for capacity in insights['capacity_rows']:
        group = capacity['group']
        season_node = tree.setdefault(group.season_id, {'season': group.season, 'courses': {}})
        course_node = season_node['courses'].setdefault(group.course_id, {'name': group.course_title, 'groups': []})
        capacity['participants'] = []
        course_node['groups'].append(capacity)
    waiting = defaultdict(list)
    for item in insights['rows']:
        group = item.planned_group_display
        if group:
            for capacity in insights['capacity_rows']:
                if capacity['group'].pk == group.pk:
                    capacity['participants'].append(item)
                    break
        else:
            waiting[item.season_id if item.season_id is not None else (season_id if season_id is not None else None)].append(item)
    season_tree = []
    for season_id, node in tree.items():
        season_tree.append({'season': node['season'], 'courses': list(node['courses'].values()), 'waiting': waiting.pop(season_id, [])})
    for season_id, items in waiting.items():
        if season_id is None:
            continue  # Open applications without a selected season are shown when a season is selected.
        season = Season.objects.filter(pk=season_id).first()
        season_tree.append({'season': season, 'courses': [], 'waiting': items})
    rows = insights['rows']
    if outcome_filter in ('preferred', 'alternative', 'unplaced', 'check', 'confirmed'):
        rows = [item for item in rows if item.quality_outcome == outcome_filter]
    return render(request, 'planning/application_plan_review.html', {
        **insights, 'current_phase': phase, 'season_tree': season_tree, 'applications': rows, 'current_season': season_filter,
        'current_course': course_filter, 'current_outcome': outcome_filter,
        'seasons': Season.objects.all().order_by('-starts_on'),
        'courses': SitePage.objects.filter(course_applications__isnull=False).distinct().order_by('title'),
        'action_groups': TrainingGroup.objects.select_related('season').order_by('season__starts_on', 'name'),
    })


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_assign(request, pk):
    from django.db import transaction
    from django.db.models import Count, Q
    from .application_planning import compatible_groups
    group_value = request.POST.get('group', '')
    with transaction.atomic():
        application = get_object_or_404(CourseApplication.objects.select_for_update(), pk=pk)
        if application.proposed_group_id and TrainingGroup.objects.filter(pk=application.proposed_group_id, planning_locked_at__isnull=False).exists():
            messages.error(request, 'Deze conceptplaatsing is goedgekeurd en vergrendeld.')
            return redirect('planning:application_detail', pk=pk)
        if application.linked_enrollment_id or application.status in (CourseApplication.Status.PROCESSED, CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST):
            messages.error(request, 'Deze aanvraag kan niet meer voorlopig worden gepland.')
            return redirect('planning:application_detail', pk=pk)
        if not group_value:
            application.proposed_group = None
            application.placement_source = 'legacy'
            application.capacity_override_by = None
            application.capacity_override_at = None
            application.save(update_fields=['proposed_group', 'placement_source', 'capacity_override_by', 'capacity_override_at', 'updated_at'])
            messages.success(request, 'Voorlopige plaatsing verwijderd.')
            return redirect('planning:application_plan_review')
        group = get_object_or_404(TrainingGroup.objects.select_for_update(), pk=group_value) if group_value.isdecimal() else None
        if not group or group.season.status == Season.Status.CLOSED or group.course_id != application.course_id or (application.season_id is not None and group.season_id != application.season_id):
            messages.error(request, 'Kies een lesgroep binnen de aangevraagde cursus en het seizoen.')
            return redirect('planning:application_detail', pk=pk)
        if group.execution_status != 'planned':
            messages.error(request, 'Deze lesgroep is al gestart of afgesloten; plaatsing is niet toegestaan.')
            return redirect('planning:application_detail', pk=pk)
        if group.planning_locked_at:
            messages.error(request, 'Deze lesgroep is goedgekeurd en vergrendeld.')
            return redirect('planning:application_detail', pk=pk)
        if not compatible_groups(application, [group]):
            messages.error(request, 'Deze lestijd is niet als beschikbaar opgegeven. Wijzig eerst de voorkeuren met de aanvrager.')
            return redirect('planning:application_detail', pk=pk)
        used = Enrollment.objects.filter(group=group, status=Enrollment.Status.PLACED).count()
        drafts = CourseApplication.objects.filter(proposed_group=group, linked_enrollment__isnull=True).exclude(pk=application.pk).count()
        over_capacity = used + drafts >= group.capacity
        if over_capacity and request.POST.get('capacity_override') != 'yes':
            messages.error(request, 'Deze groep is vol. Bevestig expliciet een capaciteitsuitzondering om toch te plaatsen.')
            return redirect('planning:application_detail', pk=pk)
        from django.utils import timezone
        application.proposed_group = group
        application.placement_source = 'manual'
        application.capacity_override_by = request.user if over_capacity else None
        application.capacity_override_at = timezone.now() if over_capacity else None
        application.save(update_fields=['proposed_group', 'placement_source', 'capacity_override_by', 'capacity_override_at', 'updated_at'])
    messages.success(request, 'Voorlopige plaatsing opgeslagen; nog niet verwerkt.')
    return redirect('planning:application_plan_review')


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_confirm(request, pk):
    from django.db import transaction
    with transaction.atomic():
        application = get_object_or_404(CourseApplication.objects.select_for_update().select_related('proposed_group'), pk=pk)
        if application.linked_enrollment_id or application.status in (CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST) or not application.proposed_group_id:
            messages.error(request, 'Deze aanvraag heeft geen bevestigbare conceptplaatsing.')
            return redirect('planning:application_plan_review')
        group = TrainingGroup.objects.select_for_update().get(pk=application.proposed_group_id)
        if group.execution_status != 'planned':
            messages.error(request, 'De cursus is gestart of afgesloten; nieuwe inschrijvingen zijn geblokkeerd.')
            return redirect('planning:application_plan_review')
        if not group.planning_locked_at:
            messages.error(request, 'Keur eerst de conceptplanning van deze lesgroep goed.')
            return redirect('planning:application_plan_review')
        if not application.linked_combination_id:
            messages.error(request, 'Koppel eerst een bestaande geleider-hondcombinatie aan deze aanvraag voordat je bevestigt.')
            return redirect('planning:application_detail', pk=pk)
        if group.season.status == Season.Status.CLOSED or group.course_id != application.course_id or (application.season_id is not None and group.season_id != application.season_id):
            messages.error(request, 'Lesgroep en aanvraag komen niet meer overeen.')
            return redirect('planning:application_plan_review')
        over_capacity = Enrollment.objects.filter(group=group, status=Enrollment.Status.PLACED).count() >= group.capacity
        if over_capacity and not application.capacity_override_by_id:
            messages.error(request, 'Lesgroep is inmiddels vol. Geen geregistreerde capaciteitsuitzondering.')
            return redirect('planning:application_plan_review')
        enrollment, created = Enrollment.objects.get_or_create(group=group, combination_id=application.linked_combination_id, defaults={'status': Enrollment.Status.PLACED, 'capacity_override_by_id': application.capacity_override_by_id if over_capacity else None, 'capacity_override_at': application.capacity_override_at if over_capacity else None})
        if not created and enrollment.status != Enrollment.Status.PLACED:
            enrollment.status = Enrollment.Status.PLACED
            enrollment.full_clean()
            enrollment.save(update_fields=['status'])
        application.linked_enrollment = enrollment
        application.proposed_group = None
        application.status = CourseApplication.Status.PROCESSED
        application.save(update_fields=['linked_enrollment', 'proposed_group', 'status', 'updated_at'])
    messages.success(request, 'Plaatsing bevestigd en aanvraag verwerkt.')
    return redirect('planning:application_plan_review')


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_link_combination(request, pk):
    application = get_object_or_404(CourseApplication, pk=pk)
    if application.linked_enrollment_id:
        messages.error(request, 'Een verwerkte aanvraag kan niet opnieuw worden gekoppeld.')
        return redirect('planning:application_detail', pk=pk)
    combination = get_object_or_404(Combination, pk=request.POST.get('combination'))
    application.linked_combination = combination
    application.save(update_fields=['linked_combination', 'updated_at'])
    messages.success(request, 'Combinatie gekoppeld.')
    return redirect('planning:application_detail', pk=pk)


def _season_application_reviews():
    """Only flag unplaced applicants once all groups are locked and drafts finalized."""
    from django.db.models import Count, Q
    seasons = Season.objects.annotate(
        total_groups=Count('groups', distinct=True),
        unlocked_groups=Count('groups', filter=Q(groups__planning_locked_at__isnull=True, groups__execution_status='planned'), distinct=True),
    ).filter(total_groups__gt=0, unlocked_groups=0).order_by('-starts_on')
    reviews = []
    for season in seasons:
        drafts = CourseApplication.objects.filter(season=season, proposed_group__isnull=False, linked_enrollment__isnull=True).exclude(status__in=[CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST])
        if drafts.exists():
            continue  # Definitive enrollment of concept placements still pending.
        count = CourseApplication.objects.filter(season=season, linked_enrollment__isnull=True).exclude(status__in=[CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST, CourseApplication.Status.PROCESSED]).count()
        if count:
            reviews.append({'season': season, 'count': count})
    return reviews


@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def application_handle(request, pk):
    """Human decision only: no automated rejection or email."""
    from django.db import transaction
    from django.utils import timezone
    from django.urls import reverse
    from urllib.parse import urlencode
    action = request.POST.get('decision', '')
    reason = request.POST.get('reason', '')
    valid_reasons = {'capacity', 'availability', 'withdrawn', 'other'}
    with transaction.atomic():
        app = get_object_or_404(CourseApplication.objects.select_for_update(), pk=pk)
        if app.linked_enrollment_id or app.status == CourseApplication.Status.PROCESSED:
            messages.error(request, 'Definitief geplaatste aanmeldingen worden via Cursusuitvoering beheerd.')
        elif action == 'reopen':
            if app.status not in (CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST):
                messages.error(request, 'Deze aanmelding is niet afgesloten of op de wachtlijst.')
            else:
                app.status = CourseApplication.Status.NEW
                app.closure_reason = ''
                app.closure_note = ''
                app.handled_at = None
                app.handled_by = None
                app.save(update_fields=['status','closure_reason','closure_note','handled_at','handled_by','updated_at'])
                messages.success(request, 'Aanmelding heropend.')
        elif action in ('close', 'waitlist'):
            if app.status in (CourseApplication.Status.REJECTED, CourseApplication.Status.WAITLIST):
                messages.error(request, 'Heropen eerst deze aanmelding om een nieuw besluit te nemen.')
            elif action == 'close' and reason not in valid_reasons:
                messages.error(request, 'Selecteer een geldige reden voor afsluiten.')
            elif action == 'waitlist' and not app.season_id:
                messages.error(request, 'Koppel eerst een seizoen voordat je een aanmelding op de wachtlijst zet.')
            else:
                app.status = CourseApplication.Status.REJECTED if action == 'close' else CourseApplication.Status.WAITLIST
                app.closure_reason = reason if action == 'close' else ''
                app.closure_note = request.POST.get('note', '').strip()[:4000]
                app.handled_at = timezone.now()
                app.handled_by = request.user
                app.proposed_group = None  # Release provisional capacity.
                app.save(update_fields=['status','closure_reason','closure_note','handled_at','handled_by','proposed_group','updated_at'])
                messages.success(request, 'Aanmelding afgehandeld. Er is geen e-mail verzonden.')
        else:
            messages.error(request, 'Ongeldige afhandelactie.')
    destination = reverse('planning:application_list')
    if app.season_id:
        destination += '?' + urlencode({'season': app.season_id, 'status': 'handled' if action != 'reopen' else 'open'})
    return redirect(destination)
