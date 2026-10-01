"""Signed, time-limited tokens for newsletter unsubscribe links.

Unsubscribing used to be authorized by an ``?email=`` query parameter, which
meant anyone who knew or guessed a subscriber's address could cancel their
subscription. Authorization now rests on a signed token that carries only the
subscriber primary key, so the email address is never exposed in a URL.
"""

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse

UNSUBSCRIBE_SALT = "newsletter-unsubscribe"
UNSUBSCRIBE_TOKEN_MAX_AGE = 30 * 24 * 3600

_signer = TimestampSigner(salt=UNSUBSCRIBE_SALT)


def generate_unsubscribe_token(subscriber_pk: int) -> str:
    """Return a signed unsubscribe token identifying only the subscriber pk."""
    return _signer.sign(str(subscriber_pk))


def unsubscribe_token_subject(token: str):
    """Return the subscriber pk encoded in ``token``, or None if it is not valid.

    Returns None for forged, tampered, expired, and malformed tokens.
    """
    if not token:
        return None

    try:
        raw_value = _signer.unsign(token, max_age=UNSUBSCRIBE_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def build_unsubscribe_url(subscriber_pk: int) -> str:
    """Absolute unsubscribe URL carrying a signed token instead of an email."""
    path = reverse("website:newsletter_unsubscribe")
    token = generate_unsubscribe_token(subscriber_pk)
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}{path}?token={token}"