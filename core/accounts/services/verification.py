import hashlib
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils import timezone

from accounts.models import EmailVerificationToken

logger = logging.getLogger(__name__)

signer = TimestampSigner()
VERIFICATION_MAX_AGE = 12 * 3600


def build_verification_link(request, token):
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}/accounts/verify-email/confirm/?token={token}"


def send_verification_email(user, verification_link):
    email = user.email
    profile = getattr(user, "profile", None)
    name = profile.first_name if profile and profile.first_name else email
    try:
        send_mail(
            subject="تایید ایمیل",
            message=(
                f"سلام {name},\n\n"
                f"برای تایید ایمیل خود روی لینک زیر کلیک کنید:\n\n"
                f"{verification_link}\n\n"
                f"اگر شما ثبت نام نکرده‌اید، این ایمیل را نادیده بگیرید."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("ایمیل تایید با موفقیت به %s ارسال شد.", email)
    except Exception as e:
        logger.error("خطا در ارسال ایمیل تایید به %s: %s", email, e)


def generate_verification_token(user):
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
    raw_token = f"verify:{user.id}:{timestamp}"
    signed_token = signer.sign(raw_token)
    EmailVerificationToken.create_token(user, raw_token)
    return signed_token


def verify_verification_token(token):
    try:
        raw_token = signer.unsign(token, max_age=VERIFICATION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        logger.warning("توکن تایید نامعتبر یا منقضی شده: %s", token[:20])
        return None

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        verification_token = EmailVerificationToken.objects.get(
            token_hash=token_hash,
            is_used=False,
        )
        if verification_token.is_valid():
            return verification_token.user_id
        logger.warning("توکن تایید منقضی شده در دیتابیس: %s", token[:20])
    except EmailVerificationToken.DoesNotExist:
        logger.warning("توکن تایید در دیتابیس یافت نشد: %s", token[:20])

    return None


def mark_verification_token_used(token):
    try:
        raw_token = signer.unsign(token, max_age=VERIFICATION_MAX_AGE)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        updated = EmailVerificationToken.objects.filter(
            token_hash=token_hash,
            is_used=False,
        ).update(is_used=True)
        return updated > 0
    except (BadSignature, SignatureExpired) as e:
        logger.warning("خطا در غیرفعال کردن توکن تایید: %s", e)
        return False
