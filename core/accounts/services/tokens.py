import hashlib
import logging

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db import transaction
from django.utils import timezone

from accounts.models import PasswordResetToken

logger = logging.getLogger(__name__)

signer = TimestampSigner()
TOKEN_MAX_AGE = 48 * 3600


def _token_fingerprint(token):
    """Non-reversible short identifier safe to write to logs."""
    return hashlib.sha256((token or "").encode()).hexdigest()[:12]


def generate_reset_token(user):
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
    raw_token = f"reset:{user.id}:{timestamp}"
    signed_token = signer.sign(raw_token)
    PasswordResetToken.create_token(user, raw_token)
    return signed_token


def verify_reset_token(token):
    try:
        raw_token = signer.unsign(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        logger.warning("توکن نامعتبر یا منقضی شده: %s", _token_fingerprint(token))
        return None

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        reset_token = PasswordResetToken.objects.get(
            token_hash=token_hash,
            is_used=False,
        )
        if reset_token.is_valid():
            return reset_token.user_id
        logger.warning("توکن بازیابی منقضی شده در دیتابیس: %s", _token_fingerprint(token))
    except PasswordResetToken.DoesNotExist:
        logger.warning("توکن در دیتابیس یافت نشد: %s", _token_fingerprint(token))

    return None


def claim_reset_token(token):
    """Atomically consume a reset token and return its user id, or None.

    The row is locked and ``is_used`` is re-checked while holding that lock, so
    of any number of concurrent attempts on the same token exactly one can
    claim it and change the password. Must be called inside a transaction so a
    later failure rolls the consumption back.
    """
    try:
        raw_token = signer.unsign(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        logger.warning("توکن بازیابی نامعتبر یا منقضی شده است.")
        return None

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with transaction.atomic():
        reset_token = (
            PasswordResetToken.objects.select_for_update()
            .filter(token_hash=token_hash, is_used=False)
            .first()
        )
        if reset_token is None:
            logger.warning("توکن بازیابی قبلاً استفاده شده یا یافت نشد.")
            return None

        if reset_token.expires_at <= timezone.now():
            logger.warning("توکن بازیابی منقضی شده است.")
            return None

        reset_token.is_used = True
        reset_token.save(update_fields=["is_used"])
        return reset_token.user_id


def mark_token_used(token):
    try:
        raw_token = signer.unsign(token, max_age=TOKEN_MAX_AGE)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        updated = PasswordResetToken.objects.filter(
            token_hash=token_hash,
            is_used=False,
        ).update(is_used=True)
        return updated > 0
    except (BadSignature, SignatureExpired) as e:
        logger.warning("خطا در غیرفعال کردن توکن بازیابی: %s", e)
        return False
