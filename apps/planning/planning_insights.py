"""Read-only planning diagnostics. Never changes proposals or enrollments."""
from collections import Counter, defaultdict
from django.db.models import Count, Q
from .models import CourseApplication, Enrollment, Season, TrainingGroup


def build_insights(season_id=None, course_id=None, phase="planning"):
    applications = CourseApplication.objects.select_related('course', 'season', 'proposed_group', 'linked_enrollment__group').exclude(
        status=CourseApplication.Status.REJECTED)
    if season_id is not None:
        applications = applications.filter(Q(season_id=season_id) | Q(season__isnull=True, proposed_group__season_id=season_id) | Q(season__isnull=True, proposed_group__isnull=True, course_id__in=TrainingGroup.objects.filter(season_id=season_id).values('course_id')))
    else:
        applications = applications.filter(Q(season__isnull=False) | Q(proposed_group__isnull=False))
    if course_id is not None:
        applications = applications.filter(course_id=course_id)
    applications = list(applications.order_by('created_at', 'pk'))
    groups = TrainingGroup.objects.select_related('course', 'season').annotate(
        confirmed=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.PLACED), distinct=True))
    if season_id is not None:
        groups = groups.filter(season_id=season_id)
    else:
        groups = groups.filter(season__status__in=[Season.Status.ACTIVE, Season.Status.DRAFT])
    if course_id is not None:
        groups = groups.filter(course_id=course_id)
    if phase == 'planning':
        groups = groups.filter(execution_status='planned')
    elif phase == 'active':
        groups = groups.filter(execution_status='active')
    elif phase == 'history':
        groups = groups.filter(execution_status__in=['completed', 'cancelled'])
    groups = list(groups.order_by('season__starts_on', 'course__title', 'day', 'starts_at', 'pk'))
    by_group = {g.pk: g for g in groups}
    if phase != 'all':
        applications = [a for a in applications if (a.linked_enrollment_id and a.linked_enrollment.group_id in by_group) or (a.proposed_group_id in by_group) or (phase == 'planning' and not a.linked_enrollment_id and not a.proposed_group_id)]
    demand = Counter()
    proposed = Counter()
    rows = []
    counts = Counter()
    for app in applications:
        prefs = app.time_preferences or {}
        for key, value in prefs.items():
            try:
                group_id = int(key)
            except (ValueError, TypeError):
                continue
            group = by_group.get(group_id)
            if group and group.season_id == app.season_id and group.course_id == app.course_id and value == 'preferred':
                demand[group_id] += 1
        group = app.linked_enrollment.group if app.linked_enrollment_id else app.proposed_group
        if app.linked_enrollment_id:
            outcome = 'confirmed'
            label = 'Verwerkt'
        elif group:
            preference = prefs.get(str(group.pk))
            outcome = 'preferred' if preference == 'preferred' else 'alternative' if preference == 'ok' else 'check'
            label = ('Open aanmelding · voorstel controleren' if app.season_id is None else {'preferred': 'Voorkeur', 'alternative': 'Alternatief', 'check': 'Controle nodig'}[outcome])
            proposed[group.pk] += 1
        else:
            eligible = [g for g in groups if (app.season_id is None or g.season_id == app.season_id) and g.course_id == app.course_id and (prefs.get(str(g.pk)) in ('preferred', 'ok') or (app.season_id is None and not prefs))]
            outcome = 'unplaced' if eligible else 'check'
            label = ('Open aanmelding · niet ingepland' if app.season_id is None else 'Niet geplaatst' if eligible else 'Controle nodig')
        if app.linked_enrollment_id:
            preference = prefs.get(str(group.pk)) if group else ''
            counts['confirmed_' + (preference if preference in ('preferred', 'ok') else 'unknown')] += 1
        else:
            counts[outcome] += 1
        app.quality_outcome = outcome
        app.quality_label = label
        app.planned_group_display = group
        app.preferred_groups_display = [by_group[int(key)] for key, val in prefs.items() if str(key).isdigit() and int(key) in by_group and val == 'preferred']
        rows.append(app)
    capacity_rows = []
    opportunities = []
    for g in groups:
        used = g.confirmed + proposed[g.pk]
        free = max(0, g.capacity - used)
        shortfall = max(0, demand[g.pk] - g.capacity)
        row = {'group': g, 'confirmed': g.confirmed, 'draft': proposed[g.pk], 'used': used,
               'free': free, 'demand': demand[g.pk], 'shortfall': shortfall,
               'percentage': min(100, round(used * 100 / g.capacity)) if g.capacity else 0}
        capacity_rows.append(row)
        if shortfall:
            opportunities.append({'kind': 'shortage', 'group': g, 'count': shortfall,
                                  'message': f'{shortfall} meer voorkeursaanvragen dan de groepscapaciteit.'})
        if free:
            compatible_waiting = sum(1 for a in rows if a.quality_outcome == 'unplaced' and
                                     (a.season_id is None or a.season_id == g.season_id) and a.course_id == g.course_id and
                                     (a.time_preferences or {}).get(str(g.pk)) in ('preferred', 'ok'))
            if compatible_waiting:
                opportunities.append({'kind': 'opportunity', 'group': g, 'count': compatible_waiting,
                                      'message': f'{free} plaatsen vrij; {compatible_waiting} nog niet geplaatste aanmeldingen geven dit moment als mogelijk op.'})
    total = len(rows)
    placed = counts['preferred'] + counts['alternative'] + counts['confirmed']
    confirmed = counts['confirmed']
    preferred = counts['preferred'] + counts['confirmed_preferred']
    alternative = counts['alternative'] + counts['confirmed_ok']
    unplaced = counts['unplaced']
    check = counts['check'] + counts['confirmed_unknown']
    return {'rows': rows, 'capacity_rows': capacity_rows, 'opportunities': opportunities,
            'total': total, 'placed': placed, 'preferred': preferred, 'alternative': alternative,
            'unplaced': unplaced, 'check': check, 'confirmed': confirmed,
            'preferred_pct': round(preferred * 100 / total) if total else 0,
            'placed_pct': round(placed * 100 / total) if total else 0}
