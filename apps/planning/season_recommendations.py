"""Conservative, capacity-aware suggestions for flexible course applications.

A recommendation is not a confirmed place. Capacity is checked again when
the administrator applies the recommendation.
"""
from django.db.models import Count, Q
from django.utils import timezone
from .models import CourseApplication, Enrollment, Season, SeasonCourseOffering, TrainingGroup


def suitable_seasons(application):
    if application.start_preference == CourseApplication.StartPreference.SPECIFIC:
        return []
    if application.linked_enrollment_id or application.proposed_group_id:
        return []
    if application.status in (
        CourseApplication.Status.PENDING_CONFIRMATION,
        CourseApplication.Status.DECLINED,
        CourseApplication.Status.PROCESSED,
        CourseApplication.Status.REJECTED,
        CourseApplication.Status.WAITLIST,
    ):
        return []
    if application.alternative_season_id and not application.alternative_accepted_at:
        return []
    if not application.course_id:
        return []

    today = timezone.localdate()
    offerings = (SeasonCourseOffering.objects
                 .select_related('season', 'course')
                 .filter(course_id=application.course_id,
                         season__status__in=[Season.Status.DRAFT, Season.Status.ACTIVE],
                         season__starts_on__gte=today)
                 .order_by('season__starts_on', 'season_id'))
    result = []
    for offering in offerings:
        if not offering.accepts_applications():
            continue
        groups = (TrainingGroup.objects
                  .filter(season=offering.season, course_id=application.course_id,
                          execution_status='planned')
                  .annotate(placed_count=Count(
                      'enrollments', filter=Q(enrollments__status=Enrollment.Status.PLACED),
                      distinct=True),
                      proposed_count=Count(
                          'proposed_applications',
                          filter=~Q(proposed_applications__status__in=[
                              CourseApplication.Status.REJECTED,
                              CourseApplication.Status.PROCESSED,
                          ]),
                          distinct=True)))
        available = sum(max(0, group.capacity - group.placed_count - group.proposed_count)
                        for group in groups)
        if available:
            result.append({'season': offering.season, 'available': available})
    return result
