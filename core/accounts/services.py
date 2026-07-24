import hashlib
import logging
from datetime import datetime

from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils import timezone
from django.conf import settings

from .models import PasswordResetToken

logger = logging.getLogger(__name__)

signer = TimestampSigner()


def generate_reset_token(user):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw_token = f"reset:{user.id}:{timestamp}"
    signed_token = signer.sign(raw_token)
    PasswordResetToken.create_token(user, raw_token)
    return signed_token


def verify_reset_token(token):
    try:
        raw_token = signer.unsign(token, max_age=48 * 3600)
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
        raw_token = signer.unsign(token, max_age=48 * 3600)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        PasswordResetToken.objects.filter(token_hash=token_hash).update(is_used=True)
    except (BadSignature, SignatureExpired):
        logger.warning("خطا در غیرفعال کردن توکن")


def send_reset_email(user, token, request):
    protocol = 'https' if request.is_secure() else 'http'
    domain = request.get_host()
    reset_link = f"{protocol}://{domain}/accounts/reset-password/?token={token}"
    email = user.email
    try:
        send_mail(
            subject='بازیابی رمز عبور',
            message=(
                f'سلام {user.profile.first_name or user.email},\n\n'
                f'برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:\n\n'
                f'{reset_link}\n\n'
                f'اگر شما درخواست بازیابی رمز نداده‌اید، این ایمیل را نادیده بگیرید.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("ایمیل بازیابی رمز عبور با موفقیت به %s ارسال شد.", email)
    except Exception as e:
        logger.error("خطا در ارسال ایمیل به %s: %s", email, e)
