"""Fixtures for public registration tests using the v21c offering gate."""
from datetime import date, time
from django.contrib.auth import get_user_model
from .models import Season, TrainingGroup, SeasonCourseOffering


def create_open_offering(course):
    season = Season.objects.create(
        name=f'Registration test {course.pk}', starts_on=date(2027, 1, 2),
        ends_on=date(2027, 3, 6), lesson_count=10, lesson_day='sat',
    )
    trainer = get_user_model().objects.create_user(username=f'registration_trainer_{course.pk}')
    TrainingGroup.objects.create(
        season=season, course=course, name='Testgroep 09:00',
        trainer=trainer, day='sat', starts_at=time(9), ends_at=time(10),
        capacity=10, lesson_dates_selected=[season.lesson_dates[0].isoformat()],
    )
    offering = SeasonCourseOffering.objects.create(season=season, course=course)
    snapshot = offering.planning_snapshot()
    assert not snapshot['issues'], snapshot['issues']
    offering.approved = True
    offering.coverage_override = True
    offering.override_reason = 'Test: instructeursdekking wordt nog afgestemd.'
    offering.approval_signature = snapshot['signature']
    offering.registration_open = True
    offering.save()
    assert offering.accepts_applications()
    return offering
