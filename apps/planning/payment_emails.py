"""Shared receipt text for manually registered and Stripe course payments."""

from decimal import Decimal

_WEEKDAYS = ('maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag')
_MONTHS = ('januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december')


def payment_received_body(payment):
    application = payment.application
    enrollment = application.linked_enrollment
    group = enrollment.group if enrollment else None
    course = application.course.title if application.course_id else (group.course_title if group else 'Cursus')
    dog = application.dog_name or (application.dog_profile.name if application.dog_profile_id else 'Niet opgegeven')
    lines = [
        f'Beste {application.first_name},',
        '',
        'We hebben je betaling ontvangen. Je inschrijving is hiermee bevestigd!',
        '',
        'Gegevens van je inschrijving',
        f'Cursist: {application.first_name} {application.last_name}'.strip(),
        f'Hond: {dog}',
        f'Cursus: {course}',
    ]
    if group:
        lines.append(f'Lesgroep: {group.name}')
        first = group.first_lesson_date
        if first:
            lines.append(f'Eerste training: {_WEEKDAYS[first.weekday()]} {first.day} {_MONTHS[first.month - 1]} {first.year}')
            if group.starts_at and group.ends_at:
                lines.append(f'Tijd: {group.starts_at:%H:%M} - {group.ends_at:%H:%M}')
        else:
            lines.append('Eerste training: De datum en tijd worden nog bekendgemaakt.')
    else:
        lines.append('Eerste training: De lesgroep en startdatum worden nog bekendgemaakt.')
    amount = payment.amount_due
    if amount is not None:
        lines.append(f'Betaald bedrag: € {Decimal(amount):.2f}'.replace('.', ','))
    lines.extend([
        f'Betalingsreferentie: {payment.reference}',
        '',
        'We kijken ernaar uit om jou en je hond te verwelkomen!',
        '',
        'Met vriendelijke groet,',
        'Mijn Hond Als Vriend',
    ])
    return '\n'.join(lines)
