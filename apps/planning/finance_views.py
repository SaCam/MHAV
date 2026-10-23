from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Season, SeasonCourseOffering, RegistrationPayment, CourseApplication, Enrollment, TrainingGroup
from .views import is_planner

@user_passes_test(is_planner, login_url='accounts:login')
def dashboard(request):
    season_id = request.GET.get('season', '')
    status = request.GET.get('status', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    payments = RegistrationPayment.objects.select_related('application__course', 'application__linked_enrollment__group__season').all()
    if season_id.isdecimal():
        payments = payments.filter(application__linked_enrollment__group__season_id=int(season_id))
    cancelled = Q(cancelled_at__isnull=False) | Q(application__linked_enrollment__status=Enrollment.Status.CANCELLED)
    if status == 'cancelled':
        payments = payments.filter(cancelled)
    elif status == 'refund_review':
        payments = payments.filter(cancelled, status=RegistrationPayment.Status.PAID)
    elif status in dict(RegistrationPayment.Status.choices):
        payments = payments.filter(status=status).exclude(cancelled)
    for field, value, suffix in [('created_at__date__gte', start, 'start'), ('created_at__date__lte', end, 'end')]:
        try:
            if value: payments = payments.filter(**{field: datetime.strptime(value, '%Y-%m-%d').date()})
        except ValueError:
            messages.error(request, f'Ongeldige datum: {suffix}')
    active = payments.exclude(cancelled)
    paid = payments.filter(status=RegistrationPayment.Status.PAID).aggregate(total=Sum('amount_due'))['total'] or Decimal('0')
    pending = active.filter(status=RegistrationPayment.Status.PENDING).aggregate(total=Sum('amount_due'))['total'] or Decimal('0')
    overdue = active.filter(status=RegistrationPayment.Status.PENDING, due_at__lt=timezone.now()).count()
    cancelled_count = payments.filter(cancelled).count()
    refund_review_count = payments.filter(cancelled, status=RegistrationPayment.Status.PAID).count()
    payment_rows = []
    for payment in payments.order_by('-created_at')[:300]:
        is_cancelled = bool(payment.cancelled_at or (payment.application.linked_enrollment_id and payment.application.linked_enrollment.status == Enrollment.Status.CANCELLED))
        label = ('Geannuleerd – terugbetaling beoordelen' if payment.status == RegistrationPayment.Status.PAID else 'Geannuleerd') if is_cancelled else ('Betaling achterstallig' if payment.status == RegistrationPayment.Status.PENDING and payment.due_at and payment.due_at < timezone.now() else payment.get_status_display())
        payment_rows.append({'payment': payment, 'label': label, 'cancelled': is_cancelled, 'review': is_cancelled and payment.status == RegistrationPayment.Status.PAID})
    return render(request, 'planning/finance_dashboard.html', {
        'payment_rows': payment_rows, 'seasons': Season.objects.all(),
        'offerings': SeasonCourseOffering.objects.select_related('season', 'course').order_by('-season__starts_on', 'course__title'),
        'selected_season': season_id, 'selected_status': status, 'start': start, 'end': end,
        'paid_total': paid, 'pending_total': pending, 'overdue_count': overdue, 'cancelled_count': cancelled_count, 'refund_review_count': refund_review_count,
        'status_choices': list(RegistrationPayment.Status.choices) + [('cancelled', 'Geannuleerd'), ('refund_review', 'Terugbetaling beoordelen')],
    })

@require_POST
@user_passes_test(is_planner, login_url='accounts:login')
def offering_settings(request, pk):
    offering = get_object_or_404(SeasonCourseOffering, pk=pk)
    raw = request.POST.get('price', '').strip().replace(',', '.')
    try:
        price = Decimal(raw) if raw else None
        if price is not None and (not price.is_finite() or price < 0 or price > 9999999 or price.as_tuple().exponent < -2):
            raise ValueError
        term = int(request.POST.get('term', '14'))
        grace = int(request.POST.get('grace', '3'))
        if not 1 <= term <= 365 or not 0 <= grace <= 60:
            raise ValueError
    except (ValueError, InvalidOperation):
        messages.error(request, 'Controleer cursusprijs, betaaltermijn (1–365) en respijtperiode (0–60).')
        return redirect('planning:finance_dashboard')
    offering.course_price = price
    offering.payment_term_days = term
    offering.grace_period_days = grace
    offering.save(update_fields=['course_price', 'payment_term_days', 'grace_period_days'])
    messages.success(request, 'Financiële instellingen opgeslagen. Bestaande betalingsverplichtingen zijn ongewijzigd.')
    return redirect('planning:finance_dashboard')


@user_passes_test(is_planner, login_url='accounts:login')
def fill_vacancy(request, pk):
    """Two-step replacement in an approved group: propose, then confirm on application page."""
    with transaction.atomic():
        group = get_object_or_404(TrainingGroup.objects.select_related('season', 'course').select_for_update(of=('self',)), pk=pk)
        occupied = Enrollment.objects.filter(group=group, status=Enrollment.Status.PLACED).count()
        if not group.planning_locked_at or group.execution_status != 'planned' or group.season.status == Season.Status.CLOSED:
            messages.error(request, 'Alleen goedgekeurde lesgroepen die nog niet gestart zijn kunnen worden aangevuld.')
            return redirect('planning:group_detail', pk=pk)
        reserved = CourseApplication.objects.filter(proposed_group=group, linked_enrollment__isnull=True).count()
        if occupied + reserved >= group.capacity:
            messages.error(request, 'Deze lesgroep heeft geen vrije plaatsen.')
            return redirect('planning:group_detail', pk=pk)
        eligible = CourseApplication.objects.filter(course_id=group.course_id, status__in=[CourseApplication.Status.NEW, CourseApplication.Status.REVIEW, CourseApplication.Status.WAITING], linked_enrollment__isnull=True, proposed_group__isnull=True, participant_confirmed_at__isnull=False).order_by('created_at')
        if request.method == 'POST':
            app_id = request.POST.get('application', '')
            app = get_object_or_404(CourseApplication.objects.select_for_update(), pk=app_id) if app_id.isdecimal() else None
            if not app or not eligible.filter(pk=app.pk).exists():
                messages.error(request, 'Deze aanvraag is niet beschikbaar voor een vervangende plaatsing.')
                return redirect('planning:finance_fill_vacancy', pk=pk)
            if app.start_preference == CourseApplication.StartPreference.SPECIFIC and group.season_id != (app.requested_season_id or app.season_id) and not (app.alternative_season_id == group.season_id and app.alternative_accepted_at):
                messages.error(request, 'De cursist moet eerst akkoord geven voor dit afwijkende seizoen.')
                return redirect('planning:finance_fill_vacancy', pk=pk)
            if app.season_id and app.season_id != group.season_id and app.start_preference == CourseApplication.StartPreference.SPECIFIC:
                messages.error(request, 'Seizoen komt niet overeen met de aanvraag.')
                return redirect('planning:finance_fill_vacancy', pk=pk)
            app.season = group.season
            app.proposed_group = group
            app.placement_source = 'manual'
            app.save(update_fields=['season', 'proposed_group', 'placement_source', 'updated_at'])
            messages.success(request, 'Vervangende conceptplaatsing voorbereid. Controleer de aanvraag en klik op Definitief plaatsen om deze te verwerken.')
            return redirect('planning:application_detail', pk=app.pk)
    return render(request, 'planning/finance_fill_vacancy.html', {'group': group, 'occupied': occupied, 'eligible': eligible})
