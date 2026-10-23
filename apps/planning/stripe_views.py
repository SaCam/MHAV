from .payment_emails import payment_received_body
"""Stripe Checkout (hosted) and signed, idempotent webhook settlement."""
from decimal import Decimal
import logging
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import CourseApplication, RegistrationPayment, RegistrationPaymentEvent, StripeCheckoutAttempt
from .notifications import notify_after_commit

logger = logging.getLogger(__name__)

def guest_payment_signer():
    return signing.TimestampSigner(salt='mhav-guest-payment-v1')


@require_http_methods(['GET', 'POST'])
def guest_checkout(request, token):
    try:
        pk = int(guest_payment_signer().unsign(token, max_age=14 * 86400))
    except (signing.BadSignature, signing.SignatureExpired, ValueError):
        return HttpResponseBadRequest('Deze betaallink is ongeldig of verlopen. Vraag een nieuwe link aan bij MHAV.')
    application = get_object_or_404(CourseApplication, pk=pk)
    if request.method == 'GET':
        payment = getattr(application, 'payment', None)
        if not payment or payment.status != RegistrationPayment.Status.PENDING or payment.cancelled_at or not payment.amount_due:
            return HttpResponse('Deze betaling is niet (meer) beschikbaar.')
        from django.shortcuts import render
        return render(request, 'planning/guest_payment.html', {'application': application, 'payment': payment, 'token': token})
    return _start_checkout(request, application, redirect_target='website:application_thanks')


@login_required
@require_POST
def checkout(request, pk):
    application = get_object_or_404(CourseApplication, pk=pk, user=request.user)
    return _start_checkout(request, application)


def _start_checkout(request, application, redirect_target='accounts:dashboard'):
    if not getattr(settings, 'STRIPE_SECRET_KEY', ''):
        messages.error(request, 'Online betalen is nog niet beschikbaar.')
        return redirect(redirect_target)
    with transaction.atomic():
        application = get_object_or_404(CourseApplication.objects.select_for_update(), pk=application.pk)
        if application.status != CourseApplication.Status.PROCESSED or not application.linked_enrollment_id:
            return HttpResponseBadRequest('Geen definitieve plaatsing.')
        payment = get_object_or_404(RegistrationPayment.objects.select_for_update(), application=application)
        if payment.status != RegistrationPayment.Status.PENDING or payment.cancelled_at or not payment.amount_due or payment.amount_due <= 0:
            messages.info(request, 'Deze betaling is niet meer beschikbaar.')
            return redirect(redirect_target)
        cents = int(payment.amount_due * 100)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.create(
                mode='payment',
                client_reference_id=str(payment.pk),
                customer_email=application.email,
                line_items=[{'price_data': {'currency': 'eur', 'unit_amount': cents, 'product_data': {'name': f'MHAV cursus - {payment.reference}'}}, 'quantity': 1}],
                success_url=request.build_absolute_uri(reverse('planning:stripe_result')) + '?status=success',
                cancel_url=request.build_absolute_uri(reverse('planning:stripe_result')) + '?status=cancel',
                metadata={'payment_id': str(payment.pk), 'reference': payment.reference},
                idempotency_key=f'mhav-checkout-{payment.pk}-{cents}-{timezone.now().strftime("%Y%m%d%H%M%S%f")}',
            )
        except stripe.StripeError:
            logger.exception('Stripe checkout creation failed for payment %s', payment.pk)
            messages.error(request, 'Betalen is tijdelijk niet beschikbaar. Probeer het later opnieuw.')
            return redirect(redirect_target)
        StripeCheckoutAttempt.objects.create(payment=payment, session_id=session.id, amount_cents=cents)
    return HttpResponseRedirect(session.url)

def result(request):
    messages.info(request, 'Je betaling wordt verwerkt. De status wordt bijgewerkt zodra de betaalprovider deze bevestigt.' if request.GET.get('status') == 'success' else 'Je kunt later opnieuw betalen via Mijn MHAV.')
    return redirect('accounts:dashboard' if request.user.is_authenticated else 'website:application_thanks')

@csrf_exempt
@require_POST
def webhook(request):
    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        return HttpResponse('Webhook niet geconfigureerd', status=503)
    try:
        event = stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), secret)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponseBadRequest('Ongeldige handtekening')
    if event['type'] not in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
        return HttpResponse(status=200)
    session = event['data']['object']
    if session.get('payment_status') != 'paid':
        return HttpResponse(status=200)
    with transaction.atomic():
        attempt = StripeCheckoutAttempt.objects.select_for_update().filter(session_id=session.get('id')).first()
        if not attempt:
            logger.error('Unknown Stripe checkout session %s', session.get('id'))
            return HttpResponse(status=200)
        payment = RegistrationPayment.objects.select_for_update().get(pk=attempt.payment_id)
        if session.get('mode') != 'payment' or str(session.get('client_reference_id')) != str(payment.pk) or session.get('currency', '').lower() != attempt.currency or session.get('amount_total') != attempt.amount_cents:
            logger.error('Stripe payment verification mismatch: %s', attempt.session_id)
            return HttpResponse(status=200)
        intent = session.get('payment_intent') or ''
        if payment.status != RegistrationPayment.Status.PENDING or payment.cancelled_at or payment.amount_due is None or int(payment.amount_due * 100) != attempt.amount_cents:
            logger.error('Paid Stripe session %s needs reconciliation: local payment already settled or amount changed', attempt.session_id)
            RegistrationPaymentEvent.objects.get_or_create(payment=payment, action='stripe_reconcile', note=f'Stripe sessie {attempt.session_id} betaald; controleer handmatig op mogelijke dubbele betaling.')
            return HttpResponse(status=200)
        payment.status = RegistrationPayment.Status.PAID
        payment.method = RegistrationPayment.Method.ONLINE
        payment.paid_at = timezone.now()
        payment.note = f'Stripe Checkout {attempt.session_id}'
        payment.save(update_fields=['status', 'method', 'paid_at', 'note', 'updated_at'])
        attempt.payment_intent_id = str(intent)
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=['payment_intent_id', 'completed_at'])
        RegistrationPaymentEvent.objects.create(payment=payment, action='stripe_paid', note=f'Gecontroleerde Stripe betaling: {attempt.session_id}', old_status='pending', new_status='paid')
        notify_after_commit('MHAV - Betaling ontvangen', payment_received_body(payment), [payment.application.email])
    return HttpResponse(status=200)
