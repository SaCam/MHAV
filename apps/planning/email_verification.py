"""Email-first application confirmation, independent of optional MHAV accounts."""
import logging
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import CourseApplication

SALT = 'mhav-registration-email-confirm-v1'
MAX_AGE = 24 * 60 * 60


def verification_url(request, application):
    token = signing.dumps({'id': application.pk, 'email': application.email.lower()}, salt=SALT)
    return request.build_absolute_uri(reverse('website:application_verify_email', args=[token]))


def send_application_verification(request, application):
    """Never grant account access; email confirmation only."""
    try:
        send_mail('MHAV - Bevestig je cursusaanmelding',
                  f'Beste {application.first_name},\n\n' + ('Een beheerder van Mijn Hond Als Vriend heeft een cursusaanmelding voor je aangemaakt. ' if application.submission_source == 'admin' else 'We hebben je cursusaanmelding ontvangen. ') + 
                  f'Bevestig binnen 24 uur je aanmelding via deze link:\n\n'
                  f'{verification_url(request, application)}\n\n'
                  'Dit bevestigt je aanmelding, niet je definitieve cursusplaats. '
                  'Een Mijn MHAV-account is niet verplicht.\n\n'
                  'Heb je je niet aangemeld? Negeer dit bericht.\n\nMijn Hond Als Vriend',
                  settings.DEFAULT_FROM_EMAIL, [application.email], fail_silently=False)
    except Exception:
        logging.getLogger(__name__).exception('Application verification email failed')
        CourseApplication.objects.filter(pk=application.pk).update(confirmation_email_status='failed')
        return False
    CourseApplication.objects.filter(pk=application.pk).update(
        confirmation_email_status='sent', confirmation_email_sent_at=timezone.now())
    return True


@require_http_methods(['GET', 'POST'])
def verify_application_email(request, token):
    try:
        data = signing.loads(token, salt=SALT, max_age=MAX_AGE)
        pk = int(data['id'])
        address = str(data['email'])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, ValueError, TypeError):
        raise Http404('Deze bevestigingslink is ongeldig of verlopen.')
    account_url = None
    account_url = None
    with transaction.atomic():
        app = get_object_or_404(CourseApplication.objects.select_for_update(), pk=pk)
        if app.email.lower() != address:
            raise Http404('Dit e-mailadres hoort niet meer bij deze aanmelding.')
        if request.method == 'POST':
            action = request.POST.get('decision', 'confirm')
            if action not in ('confirm', 'decline'):
                raise Http404('Ongeldige keuze.')
            if app.status == CourseApplication.Status.DECLINED:
                pass  # A declined invitation cannot be reactivated with an old link.
            elif app.participant_confirmed_at:
                pass  # Already confirmed: a repeated click cannot decline it.
            elif action == 'decline':
                if app.submission_source == 'admin' and app.status == CourseApplication.Status.PENDING_CONFIRMATION:
                    app.participant_declined_at = timezone.now()
                    app.status = CourseApplication.Status.DECLINED
                    app.save(update_fields=['participant_declined_at', 'status', 'updated_at'])
            else:
                now = timezone.now()
                app.email_verified_at = app.email_verified_at or now
                app.participant_confirmed_at = now
                if app.status == CourseApplication.Status.PENDING_CONFIRMATION:
                    app.status = CourseApplication.Status.NEW
                app.save(update_fields=['email_verified_at', 'participant_confirmed_at', 'status', 'updated_at'])
            if action == 'confirm' and app.participant_confirmed_at and request.POST.get('create_account') == 'on':
                # Reuse the existing account-claim handler; it enforces account
                # ownership and password validation. Never auto-link by email.
                from .views import _claim_signer
                from django.shortcuts import redirect
                account_token = _claim_signer().sign(str(app.pk))
                return redirect('website:application_account_claim', token=account_token)
    return render(request, 'planning/application_verify_email.html', {
        'application': app, 'verified': app.participant_confirmed_at is not None,
        'declined': app.status == CourseApplication.Status.DECLINED, 'token': token,
    })


from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect

@require_POST
def resend_application_verification(request):
    pk = request.session.get('last_course_application_id')
    app = CourseApplication.objects.filter(pk=pk).first() if pk else None
    if app and not app.email_verified_at:
        # Session-scoped, not an arbitrary application ID. Rate limiting is
        # advisable before public deployment.
        if send_application_verification(request, app):
            messages.success(request, 'Een nieuwe bevestigingslink is verzonden.')
        else:
            messages.error(request, 'Verzenden is mislukt. Probeer het later opnieuw.')
    return redirect('website:application_thanks')
