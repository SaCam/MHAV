from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import TrainingGroup, Enrollment, Season


def _admin(user):
    return user.is_active and (user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists())


def _trainer(user):
    return user.is_active and user.groups.filter(name='MHAV - Trainer').exists()


def _allowed(user, group=None):
    if not (_admin(user) or _trainer(user)):
        raise PermissionDenied
    if group is not None and not (_admin(user) or group.trainer_id == user.pk):
        raise PermissionDenied


@login_required
def execution_list(request):
    _allowed(request.user)
    groups = TrainingGroup.objects.select_related('season','course','trainer').annotate(placed_count=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.PLACED)))
    if not _admin(request.user):
        groups = groups.filter(trainer=request.user)
    groups = groups.filter(Q(placed_count__gt=0) | Q(execution_status__in=['active','completed','cancelled']))
    status = request.GET.get('status', '')
    if status in dict(TrainingGroup.ExecutionStatus.choices):
        groups = groups.filter(execution_status=status)
    return render(request, 'planning/execution_list.html', {'groups':groups, 'statuses':TrainingGroup.ExecutionStatus.choices, 'current_status':status})


@login_required
def execution_detail(request, pk):
    group = get_object_or_404(TrainingGroup.objects.select_related('season','course','trainer'), pk=pk)
    _allowed(request.user, group)
    enrollments = list(group.enrollments.filter(status=Enrollment.Status.PLACED).select_related('combination__handler','combination__dog').order_by('created_at','pk'))
    return render(request, 'planning/execution_detail.html', {'group':group,'enrollments':enrollments, 'dates':group.scheduled_dates, 'pending_count':sum(e.outcome==Enrollment.Outcome.PENDING for e in enrollments), 'is_admin':_admin(request.user)})


@login_required
@require_POST
def execution_action(request, pk):
    with transaction.atomic():
        group = get_object_or_404(TrainingGroup.objects.select_for_update(), pk=pk)
        _allowed(request.user, group)
        action = request.POST.get('action')
        placed = group.enrollments.filter(status=Enrollment.Status.PLACED)
        if action == 'start':
            if group.execution_status != 'planned' or not placed.exists():
                messages.error(request, 'Deze lesgroep kan niet worden gestart.')
            else:
                group.execution_status='active'
                group.execution_started_at=timezone.now()
                group.save(update_fields=['execution_status','execution_started_at'])
                messages.success(request, 'Cursus is gestart.')
        elif action == 'outcome':
            if group.execution_status != 'active':
                messages.error(request, 'Eindresultaten kunnen alleen tijdens een actieve cursus worden gewijzigd.')
            else:
                enrollment = get_object_or_404(placed.select_for_update(), pk=request.POST.get('enrollment_id'))
                outcome = request.POST.get('outcome')
                if outcome not in dict(Enrollment.Outcome.choices):
                    messages.error(request, 'Ongeldig eindresultaat.')
                else:
                    enrollment.outcome=outcome
                    enrollment.save(update_fields=['outcome'])
                    messages.success(request, 'Eindresultaat opgeslagen.')
        elif action == 'close':
            if group.execution_status != 'active' or not placed.exists() or placed.filter(outcome=Enrollment.Outcome.PENDING).exists():
                messages.error(request, 'Vul eerst alle eindresultaten in voordat je de lesgroep afsluit.')
            else:
                group.execution_status='completed'
                group.execution_closed_at=timezone.now()
                group.execution_closed_by=request.user
                group.save(update_fields=['execution_status','execution_closed_at','execution_closed_by'])
                messages.success(request, 'Lesgroep definitief afgesloten.')
        elif action == 'reopen' and _admin(request.user):
            if group.execution_status != 'completed':
                messages.error(request, 'Alleen een afgeronde lesgroep kan worden heropend.')
            else:
                group.execution_status='active'
                group.execution_closed_at=None
                group.execution_closed_by=None
                group.save(update_fields=['execution_status','execution_closed_at','execution_closed_by'])
                messages.success(request, 'Lesgroep heropend.')
        elif action == 'cancel' and _admin(request.user):
            if group.execution_status != 'planned':
                messages.error(request, 'Alleen een nog niet gestarte lesgroep kan worden geannuleerd.')
            else:
                group.execution_status='cancelled'
                group.execution_closed_at=timezone.now()
                group.execution_closed_by=request.user
                group.save(update_fields=['execution_status','execution_closed_at','execution_closed_by'])
                messages.success(request, 'Lesgroep geannuleerd.')
        else:
            messages.error(request, 'Deze actie is niet toegestaan.')
    return redirect('planning:execution_detail', pk=pk)
