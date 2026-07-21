import jwt
import logging
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import PasswordResetToken

logger = logging.getLogger(__name__)

PASSWORD_RESET_TOKEN_LIFETIME = timedelta(hours=48)


def generate_password_reset_token(user):
    PasswordResetToken.objects.filter(user=user, is_used=False).delete()

    now = timezone.now()
    exp = now + PASSWORD_RESET_TOKEN_LIFETIME

    payload = {
        'user_id': user.id,
        'purpose': 'password_reset',
        'exp': exp.timestamp(),
        'iat': now.timestamp(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=exp,
    )
    logger.info("Password reset token generated for user %s", user.email)
    return token


def verify_password_reset_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        logger.warning("Invalid password reset token: %s", e)
        return None

    if payload.get('purpose') != 'password_reset':
        return None

    token_obj = PasswordResetToken.objects.filter(
        token=token, is_used=False
    ).first()
    if not token_obj or not token_obj.is_valid():
        return None

    return payload.get('user_id')


def mark_token_as_used(token):
    PasswordResetToken.objects.filter(token=token).update(is_used=True)
    logger.info("Password reset token marked as used")


def cleanup_expired_tokens():
    deleted, _ = PasswordResetToken.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    logger.info("Cleaned up %d expired password reset tokens", deleted)
    return deleted