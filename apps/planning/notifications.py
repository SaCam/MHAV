"""Transactional course application notifications; no database migration needed."""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

log = logging.getLogger(__name__)


def _deliver(subject, body, recipients):
    recipients = [email for email in recipients if email]
    if not recipients:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    except Exception:
        log.exception('MHAV notification could not be delivered: %s', subject)


def notify_after_commit(subject, body, recipients):
    """Never send an email about an uncommitted or rolled-back database change."""
    transaction.on_commit(lambda: _deliver(subject, body, recipients))


def participant_confirmed(application):
    notify_after_commit(
        'MHAV - Je cursusaanmelding is bevestigd',
        f'Beste {application.first_name},\n\nJe aanmelding voor {application.course or "een cursus"} is bevestigd. '
        'Dit is nog geen definitieve cursusplaats. We nemen contact met je op zodra de indeling bekend is.\n\nMijn Hond Als Vriend',
        [application.email],
    )
    admin = getattr(settings, 'MHAV_REGISTRATION_NOTIFICATION_EMAIL', '').strip()
    if admin:
        notify_after_commit(
            'MHAV - Nieuwe bevestigde cursusaanmelding',
            f'Aanmelding #{application.pk}: {application.first_name} {application.last_name}, '
            f'{application.course or "cursus onbekend"}. Bekijk de aanmelding in de cursusadministratie.',
            [admin],
        )


def participant_declined(application):
    admin = getattr(settings, 'MHAV_REGISTRATION_NOTIFICATION_EMAIL', '').strip()
    if admin:
        notify_after_commit(
            'MHAV - Cursist heeft aanmelding afgewezen',
            f'Aanmelding #{application.pk} is door de cursist afgewezen. Controleer de cursusadministratie.',
            [admin],
        )


def placement_confirmed(application, group):
    notify_after_commit(
        'MHAV - Je cursusplaats is bevestigd',
        f'Beste {application.first_name},\n\nJe bent geplaatst voor {application.course or "je cursus"} '
        f'in lesgroep {group}.\n\nMeer informatie over de start en praktische afspraken volgt via MHAV.\n\nMijn Hond Als Vriend',
        [application.email],
    )


def alternative_accepted(application):
    notify_after_commit(
        'MHAV - Andere cursusperiode geaccepteerd',
        f'Beste {application.first_name},\n\nJe hebt het voorstel voor cursusperiode '
        f'{application.alternative_season} geaccepteerd. Dit is nog geen definitieve cursusplaats.\n\nMijn Hond Als Vriend',
        [application.email],
    )


def application_closed(application, waitlisted=False):
    if waitlisted:
        subject = 'MHAV - Je staat op de wachtlijst'
        message = 'Je cursusaanmelding is op de wachtlijst geplaatst. We informeren je zodra er meer bekend is.'
    else:
        subject = 'MHAV - Bericht over je cursusaanmelding'
        message = 'Je cursusaanmelding is afgesloten zonder plaatsing. Neem contact op met MHAV als je vragen hebt.'
    notify_after_commit(subject, f'Beste {application.first_name},\n\n{message}\n\nMijn Hond Als Vriend', [application.email])
