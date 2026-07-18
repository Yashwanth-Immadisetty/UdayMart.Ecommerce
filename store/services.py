"""OTP, notification, and provider helpers for Uday Mart.

The website deliberately keeps all provider credentials in Render environment
variables.  No API secret, password, or one-time code is stored in this file
or committed to Git.
"""

import base64
import json
import logging
import re
import secrets
from datetime import timedelta
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from .models import CustomerProfile, OTPChallenge, Order, OrderNotification


logger = logging.getLogger(__name__)


class PhoneNumberError(ValueError):
    """The supplied number cannot be used with the SMS provider."""


class OTPConfigurationError(RuntimeError):
    """A required delivery provider has not been configured."""


class OTPDeliveryError(RuntimeError):
    """A provider could not deliver or validate an OTP."""


class OTPRateLimitError(RuntimeError):
    """An OTP was requested too recently or too often."""


def normalize_phone(value):
    """Return an Indian/local input as E.164, or reject an unsafe number.

    Customers can enter a normal ten-digit Indian number.  International
    E.164 input is also accepted, which keeps the stored value compatible
    with Twilio Verify and WhatsApp.
    """

    raw = str(value or '').strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if raw.startswith('00'):
        raw = '+' + raw[2:]
    elif not raw.startswith('+') and raw.isdigit() and len(raw) == 10:
        raw = '+91' + raw
    elif not raw.startswith('+') and raw.isdigit() and raw.startswith('91') and len(raw) == 12:
        raw = '+' + raw

    if not re.fullmatch(r'\+[1-9]\d{7,14}', raw):
        raise PhoneNumberError('Enter a valid mobile number, for example 9876543210.')
    return raw


def otp_auth_enabled():
    return bool(getattr(settings, 'OTP_AUTH_ENABLED', False))


def _email_is_configured():
    """Console email is allowed locally; production requires an SMTP host."""

    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if settings.DEBUG and not backend.endswith('smtp.EmailBackend'):
        return True
    return bool(getattr(settings, 'EMAIL_HOST', '') and getattr(settings, 'DEFAULT_FROM_EMAIL', ''))


def _twilio_verify_is_configured():
    return all([
        getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
        getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
        getattr(settings, 'TWILIO_VERIFY_SERVICE_SID', ''),
    ])


def otp_delivery_is_configured():
    return _email_is_configured() and _twilio_verify_is_configured()


def otp_configuration_message():
    missing = []
    if not _email_is_configured():
        missing.append('email SMTP settings')
    if not _twilio_verify_is_configured():
        missing.append('Twilio Verify settings')
    return ', '.join(missing) if missing else ''


def _twilio_post(url, payload):
    """Make a form-encoded Twilio API request without adding a Python SDK."""

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    if not account_sid or not auth_token:
        raise OTPConfigurationError('Twilio account credentials have not been configured.')

    credentials = base64.b64encode(f'{account_sid}:{auth_token}'.encode('utf-8')).decode('ascii')
    request = urlrequest.Request(
        url,
        data=urlparse.urlencode(payload).encode('utf-8'),
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )
    try:
        with urlrequest.urlopen(request, timeout=getattr(settings, 'TWILIO_REQUEST_TIMEOUT', 10)) as response:
            return json.loads(response.read().decode('utf-8'))
    except urlerror.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8'))
            provider_message = payload.get('message', 'Twilio rejected the request.')
        except Exception:  # pragma: no cover - defensive provider parsing
            provider_message = 'Twilio rejected the request.'
        logger.warning('Twilio request failed: %s', provider_message)
        raise OTPDeliveryError('The mobile verification service could not complete the request.') from exc
    except (urlerror.URLError, TimeoutError, ValueError) as exc:
        logger.warning('Twilio request could not be completed: %s', exc)
        raise OTPDeliveryError('The mobile verification service is temporarily unavailable.') from exc


def _enforce_otp_send_limit(user, purpose):
    now = timezone.now()
    cooldown = int(getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60))
    hourly_limit = int(getattr(settings, 'OTP_MAX_SENDS_PER_HOUR', 5))
    recent = OTPChallenge.objects.filter(user=user, purpose=purpose, created_at__gte=now - timedelta(hours=1))
    latest = recent.order_by('-created_at').first()

    if latest and latest.created_at > now - timedelta(seconds=cooldown):
        remaining = max(1, int((latest.created_at + timedelta(seconds=cooldown) - now).total_seconds()))
        raise OTPRateLimitError(f'Please wait {remaining} seconds before requesting another code.')
    if recent.count() >= hourly_limit:
        raise OTPRateLimitError('Too many code requests. Please try again in one hour.')


def send_email_otp(user, purpose):
    """Create a hashed six-digit email code and send it to the customer."""

    if not _email_is_configured():
        raise OTPConfigurationError('Email delivery has not been configured.')
    _enforce_otp_send_limit(user, purpose)

    code = f'{secrets.randbelow(1_000_000):06d}'
    now = timezone.now()
    challenge = OTPChallenge.objects.create(
        user=user,
        purpose=purpose,
        recipient=user.email,
        code_hash=make_password(code),
        expires_at=now + timedelta(seconds=int(getattr(settings, 'OTP_CODE_EXPIRY_SECONDS', 600))),
    )
    purpose_text = 'complete your Uday Mart registration' if purpose == OTPChallenge.PURPOSE_REGISTRATION else 'sign in to Uday Mart'
    try:
        sent = send_mail(
            subject='Your Uday Mart verification code',
            message=(
                f'Your Uday Mart verification code is {code}.\n\n'
                f'Use it to {purpose_text}. The code expires in 10 minutes.\n'
                'If you did not request this code, you can ignore this email.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        challenge.delete()
        logger.exception('Could not send email OTP to user %s', user.pk)
        raise OTPDeliveryError('We could not send the email code. Please try again shortly.') from exc
    if sent != 1:
        challenge.delete()
        raise OTPDeliveryError('We could not send the email code. Please try again shortly.')
    return challenge


def verify_email_otp(user, purpose, code):
    """Check the latest active email code and return ``(valid, message)``."""

    now = timezone.now()
    challenge = OTPChallenge.objects.filter(
        user=user,
        purpose=purpose,
        channel=OTPChallenge.CHANNEL_EMAIL,
        verified_at__isnull=True,
    ).order_by('-created_at').first()
    if not challenge or challenge.expires_at <= now:
        return False, 'This email code has expired. Request a new one.'

    maximum_attempts = int(getattr(settings, 'OTP_MAX_ATTEMPTS', 5))
    if challenge.attempts >= maximum_attempts:
        return False, 'Too many incorrect attempts. Request a new email code.'

    challenge.attempts += 1
    if check_password(code, challenge.code_hash):
        challenge.verified_at = now
        challenge.save(update_fields=['attempts', 'verified_at'])
        return True, ''

    challenge.save(update_fields=['attempts'])
    return False, 'The email code is incorrect.'


def send_sms_otp(phone):
    if not _twilio_verify_is_configured():
        raise OTPConfigurationError('Twilio Verify has not been configured.')
    service_sid = settings.TWILIO_VERIFY_SERVICE_SID
    response = _twilio_post(
        f'https://verify.twilio.com/v2/Services/{service_sid}/Verifications',
        {'To': phone, 'Channel': 'sms'},
    )
    if response.get('status') not in {'pending', 'approved'}:
        raise OTPDeliveryError('We could not send the SMS code. Please try again shortly.')
    return response


def verify_sms_otp(phone, code):
    if not _twilio_verify_is_configured():
        raise OTPConfigurationError('Twilio Verify has not been configured.')
    service_sid = settings.TWILIO_VERIFY_SERVICE_SID
    response = _twilio_post(
        f'https://verify.twilio.com/v2/Services/{service_sid}/VerificationCheck',
        {'To': phone, 'Code': code},
    )
    return response.get('status') == 'approved'


def request_dual_otp(user, purpose):
    """Send independent email and SMS codes for a registration/login challenge."""

    if not otp_delivery_is_configured():
        raise OTPConfigurationError(f'OTP delivery is not ready: {otp_configuration_message()}.')
    try:
        profile = user.customer_profile
    except CustomerProfile.DoesNotExist as exc:
        raise OTPDeliveryError('This account does not have a registered mobile number.') from exc

    send_email_otp(user, purpose)
    send_sms_otp(profile.phone)


def _record_notification(order, channel, status, provider_message_id='', error_message=''):
    OrderNotification.objects.update_or_create(
        order=order,
        event=OrderNotification.EVENT_ORDER_CONFIRMATION,
        channel=channel,
        defaults={
            'status': status,
            'provider_message_id': provider_message_id[:80],
            'error_message': error_message[:2000],
            'sent_at': timezone.now() if status == OrderNotification.STATUS_SENT else None,
        },
    )


def _order_message(order):
    items = '\n'.join(f'- {item.product_name} x {item.quantity}' for item in order.items.all())
    tracking_url = f"{getattr(settings, 'SITE_URL', '').rstrip('/')}/order/{order.order_id}/"
    return (
        f'Hello {order.full_name},\n\n'
        f'Your Uday Mart order {order.order_id} has been placed successfully.\n'
        f'Total: INR {order.total_price:.2f}\n\n'
        f'Items:\n{items}\n\n'
        f'Track your order: {tracking_url}\n\n'
        'Thank you for shopping with Uday Mart.'
    )


def _send_order_email(order):
    if not getattr(settings, 'ORDER_EMAIL_NOTIFICATIONS_ENABLED', True):
        _record_notification(order, OrderNotification.CHANNEL_EMAIL, OrderNotification.STATUS_SKIPPED, error_message='Email order notifications are disabled.')
        return
    if not order.user.email:
        _record_notification(order, OrderNotification.CHANNEL_EMAIL, OrderNotification.STATUS_SKIPPED, error_message='Customer has no email address.')
        return
    if not _email_is_configured():
        _record_notification(order, OrderNotification.CHANNEL_EMAIL, OrderNotification.STATUS_SKIPPED, error_message='Email SMTP is not configured.')
        return
    try:
        sent = send_mail(
            subject=f'Uday Mart order confirmed: {order.order_id}',
            message=_order_message(order),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        if sent != 1:
            raise OTPDeliveryError('Email backend returned no delivered messages.')
    except Exception as exc:
        logger.exception('Order confirmation email failed for %s', order.order_id)
        _record_notification(order, OrderNotification.CHANNEL_EMAIL, OrderNotification.STATUS_FAILED, error_message=str(exc))
        return
    _record_notification(order, OrderNotification.CHANNEL_EMAIL, OrderNotification.STATUS_SENT)


def _whatsapp_sender():
    sender = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')
    return sender if sender.startswith('whatsapp:') else f'whatsapp:{sender}'


def _send_order_whatsapp(order):
    if not getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        _record_notification(order, OrderNotification.CHANNEL_WHATSAPP, OrderNotification.STATUS_SKIPPED, error_message='WhatsApp order notifications are disabled.')
        return
    try:
        profile = order.user.customer_profile
    except CustomerProfile.DoesNotExist:
        _record_notification(order, OrderNotification.CHANNEL_WHATSAPP, OrderNotification.STATUS_SKIPPED, error_message='Customer has no registered mobile number.')
        return
    if not profile.phone_is_verified or not profile.whatsapp_opt_in:
        _record_notification(order, OrderNotification.CHANNEL_WHATSAPP, OrderNotification.STATUS_SKIPPED, error_message='Customer has not verified and opted in with this WhatsApp number.')
        return

    content_sid = getattr(settings, 'TWILIO_WHATSAPP_CONTENT_SID', '')
    sender = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')
    if not all([getattr(settings, 'TWILIO_ACCOUNT_SID', ''), getattr(settings, 'TWILIO_AUTH_TOKEN', ''), sender, content_sid]):
        _record_notification(order, OrderNotification.CHANNEL_WHATSAPP, OrderNotification.STATUS_SKIPPED, error_message='Twilio WhatsApp sender or approved template is not configured.')
        return

    tracking_url = f"{getattr(settings, 'SITE_URL', '').rstrip('/')}/order/{order.order_id}/"
    content_variables = json.dumps({
        '1': order.full_name,
        '2': order.order_id,
        '3': f'INR {order.total_price:.2f}',
        '4': tracking_url,
    })
    try:
        response = _twilio_post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
            {
                'From': _whatsapp_sender(),
                'To': f'whatsapp:{profile.phone}',
                'ContentSid': content_sid,
                'ContentVariables': content_variables,
            },
        )
    except Exception as exc:
        logger.exception('WhatsApp order confirmation failed for %s', order.order_id)
        _record_notification(order, OrderNotification.CHANNEL_WHATSAPP, OrderNotification.STATUS_FAILED, error_message=str(exc))
        return
    _record_notification(
        order,
        OrderNotification.CHANNEL_WHATSAPP,
        OrderNotification.STATUS_SENT,
        provider_message_id=response.get('sid', ''),
    )


def send_order_confirmation(order_id):
    """Attempt both notifications after checkout without jeopardising the order."""

    try:
        order = Order.objects.select_related('user').prefetch_related('items').get(pk=order_id)
    except Order.DoesNotExist:
        return
    _send_order_email(order)
    _send_order_whatsapp(order)
