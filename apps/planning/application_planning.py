"""Conservative FIFO planner: preferences are authoritative; drafts never occupy enrollments."""
from collections import defaultdict
from django.db.models import Count, Q
from .models import CourseApplication, Enrollment, TrainingGroup, Season

ELIGIBLE = (CourseApplication.Status.NEW, CourseApplication.Status.REVIEW, CourseApplication.Status.WAITING)

def compatible_groups(application, groups):
    preferences = application.time_preferences or {}
    choices = []
    for group in groups:
        if group.execution_status != 'planned' or group.course_id != application.course_id or ((application.season_id or application.requested_season_id) is not None and group.season_id != (application.season_id or application.requested_season_id)):
            continue
        preference = preferences.get(str(group.pk), '')
        # No explicit response is NOT consent to a different lesson time.
        if preference not in ('preferred', 'ok'):
            # Open applications did not select a season/group, so offer an
            # explicitly reviewable proposal instead of assuming a preference.
            if application.season_id is not None or application.requested_season_id is not None or preferences:
                continue
            choices.append((2, group))
            continue
        choices.append((0 if preference == 'preferred' else 1, group))
    return sorted(choices, key=lambda x: (x[0], x[1].starts_at, x[1].pk))

def manually_assignable_groups(application, groups):
    """Show all unlocked planned groups for the course, regardless of preferences.

    Administrator choices are intentionally broader than automatic planning.
    Consent for a different specifically requested season is still enforced
    at final placement, not at the draft stage.
    """
    preferences = application.time_preferences or {}
    choices = []
    for group in groups:
        if group.execution_status != 'planned' or group.course_id != application.course_id:
            continue
        preference = preferences.get(str(group.pk), '')
        priority = (0 if preference == 'preferred' else
                    1 if preference == 'ok' else
                    3 if preference == 'unavailable' else 2)
        choices.append((priority, group))
    return [group for _, group in sorted(
        choices, key=lambda item: (item[0], item[1].season.starts_on if hasattr(item[1], 'season') else '',
                                   item[1].starts_at, item[1].pk))]


def generate_proposals(season_id=None, course_id=None):
    """Fill free slots FIFO, preserving existing manual proposals. Caller holds transaction locks."""
    applications_qs = CourseApplication.objects.select_for_update().filter(
        status__in=ELIGIBLE, course__isnull=False,
        proposed_group__isnull=True, linked_enrollment__isnull=True,
    )
    if season_id is not None:
        applications_qs = applications_qs.filter(Q(season_id=season_id) | Q(season__isnull=True, requested_season_id=season_id) | Q(season__isnull=True, requested_season__isnull=True))
    if course_id is not None:
        applications_qs = applications_qs.filter(course_id=course_id)
    applications = list(applications_qs.order_by('created_at', 'pk'))
    # PostgreSQL cannot combine FOR UPDATE with GROUP BY (introduced by annotate Count).
    # Lock the base rows first, then fetch occupancy in a separate aggregate query.
    group_qs = TrainingGroup.objects.select_for_update().filter(
        season__status__in=[Season.Status.DRAFT, Season.Status.ACTIVE], execution_status='planned'
    )
    if season_id is not None:
        group_qs = group_qs.filter(season_id=season_id)
    if course_id is not None:
        group_qs = group_qs.filter(course_id=course_id)
    groups = [g for g in group_qs.order_by('pk') if not g.planning_locked_at]
    occupied_by_group = dict(Enrollment.objects.filter(
        group_id__in=[g.pk for g in groups], status=Enrollment.Status.PLACED
    ).values('group_id').annotate(total=Count('pk')).values_list('group_id', 'total'))
    group_map = defaultdict(list)
    for group in groups:
        group_map[(group.season_id, group.course_id)].append(group)
    remaining = {g.pk: max(0, g.capacity - occupied_by_group.get(g.pk, 0)) for g in groups}
    existing = CourseApplication.objects.filter(proposed_group__isnull=False).values_list('proposed_group_id', flat=True)
    for group_id in existing:
        if group_id in remaining:
            remaining[group_id] -= 1
    placed = 0
    unplaced = 0
    for application in applications:
        target_season_id = application.season_id or application.requested_season_id
        if target_season_id is None:
            # An open application is only proposed for the explicitly selected
            # season. It is never silently claimed by a season-wide run.
            options = compatible_groups(application, group_map[(season_id, application.course_id)])
        else:
            options = compatible_groups(application, group_map[(target_season_id, application.course_id)])
        # A specifically requested season must never be silently changed.
        if application.start_preference == CourseApplication.StartPreference.SPECIFIC and application.requested_season_id:
            options = [(rank, group) for rank, group in options if group.season_id == application.requested_season_id]
        available = [(rank, group) for rank, group in options if remaining[group.pk] > 0]
        if not available:
            unplaced += 1
            continue
        # Among equally preferred groups, preserve scarce alternatives for other applicants.
        rank = available[0][0]
        candidates = [group for r, group in available if r == rank]
        selected = max(candidates, key=lambda g: (remaining[g.pk], -g.pk))
        application.proposed_group = selected
        application.placement_source = 'automatic'
        application.save(update_fields=['proposed_group', 'placement_source', 'updated_at'])
        remaining[selected.pk] -= 1
        placed += 1
    return placed, unplaced
