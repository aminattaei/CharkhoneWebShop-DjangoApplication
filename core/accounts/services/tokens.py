import hashlib
import logging
from datetime import datetime

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

from accounts.models import PasswordResetToken

logger = logging.getLogger(__name__)

signer = TimestampSigner()
TOKEN_MAX_AGE = 48 * 3600


def generate_reset_token(user):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw_token = f"reset:{user.id}:{timestamp}"
    signed_token = signer.sign(raw_token)
    PasswordResetToken.create_token(user, raw_token)
    return signed_token


def verify_reset_token(token):
    try:
        raw_token = signer.unsign(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        logger.warning("توکن نامعتبر یا منقضی شده: %s", token[:20])
        return None

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        reset_token = PasswordResetToken.objects.get(
            token_hash=token_hash,
            is_used=False,
        )
        if reset_token.is_valid():
            return reset_token.user_id
    except PasswordResetToken.DoesNotExist:
        logger.warning("توکن در دیتابیس یافت نشد: %s", token[:20])

    return None


def mark_token_used(token):
    try:
        raw_token = signer.unsign(token, max_age=TOKEN_MAX_AGE)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        PasswordResetToken.objects.filter(token_hash=token_hash).update(is_used=True)
    except (BadSignature, SignatureExpired):
        logger.warning("خطا در غیرفعال کردن توکن")