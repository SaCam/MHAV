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


def public_application(request):
    """Guest-friendly intake; creates neither account nor placement."""
    initial = {}
    if request.user.is_authenticated:
        u = request.user
        initial.update(first_name=u.first_name, last_name=u.last_name, email=u.email)
        profile = getattr(u, 'member_profile', None)
        if profile:
            for field in ('phone', 'street', 'house_number', 'postal_code', 'city'):
                initial[field] = getattr(profile, field, '')
    form = CourseApplicationForm(request.POST or None, initial=initial if request.method != 'POST' else None)
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
    groups = _offered_times(selected_season if selected_season and str(selected_season).isdigit() else None,
                            selected_course if selected_course and str(selected_course).isdigit() else None)
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
                application.privacy_accepted_at = timezone.now()
                application.time_preferences = preferences
                if request.user.is_authenticated:
                    application.user = request.user
                application.save()
            request.session['last_course_application_id'] = application.pk
            # Email verification is sent on demand; no account is created here.
            return redirect('website:application_thanks')
    visible_groups = _offered_times()
    return render(request, 'planning/application_form.html', {'form': form, 'groups': visible_groups,
        'posted_preferences': request.POST if request.method == 'POST' else {},
        'preference_error': preference_error})


def application_thanks(request):
    pk = request.session.get('last_course_application_id')
    application = CourseApplication.objects.filter(pk=pk).first() if pk else None
    return render(request, 'planning/application_thanks.html', {'application': application})


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
        return render(request, 'planning/application_account_claim.html', {'existing': True})
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
    status = request.GET.get('status', '')
    applications = CourseApplication.objects.select_related('course','season').all()
    if status in CourseApplication.Status.values:
        applications = applications.filter(status=status)
    return render(request, 'planning/applications.html', {
        'applications': applications[:250], 'total': applications.count(),
        'statuses': CourseApplication.Status.choices, 'current_status': status,
    })


@user_passes_test(is_planner, login_url='accounts:login')
def application_detail(request, pk):
    application = get_object_or_404(CourseApplication.objects.select_related('course','season','user'), pk=pk)
    form = ApplicationReviewForm(request.POST or None, instance=application)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Aanmelding bijgewerkt.')
        return redirect('planning:application_detail', pk=pk)
    return render(request, 'planning/application_detail.html', {'application':application, 'form':form})


def is_trainer(user):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or user.groups.filter(name='MHAV - Trainer').exists()
    )


@user_passes_test(is_trainer, login_url='accounts:login')
def trainer_seasons(request):
    seasons = Season.objects.filter(status=Season.Status.DRAFT).order_by('starts_on')
    responses = {r.season_id: r for r in TrainerSeasonAvailability.objects.filter(trainer=request.user)}
    return render(request, 'planning/trainer_seasons.html', {
        'seasons_with_responses': [(season, responses.get(season.pk)) for season in seasons],
    })


@user_passes_test(is_trainer, login_url='accounts:login')
def trainer_availability(request, pk):
    season = get_object_or_404(Season, pk=pk)
    if season.status != Season.Status.DRAFT:
        raise Http404('De beschikbaarheid van dit seizoen is gesloten.')

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
                offering.approved = False
                offering.registration_open = False
                offering.save(update_fields=['approved', 'registration_open'])
                messages.success(request, 'Goedkeuring ingetrokken.')
        return redirect('planning:season_course_offerings', pk=pk)
    rows = []
    for course in courses:
        offering = offerings.get(course.pk) or SeasonCourseOffering(season=season, course=course)
        snapshot = offering.planning_snapshot()
        rows.append({'course': course, 'offering': offering, 'snapshot': snapshot,
                     'valid': offering.approval_valid(snapshot), 'open': offering.accepts_applications()})
    return render(request, 'planning/season_course_offerings.html', {'season': season, 'rows': rows})
