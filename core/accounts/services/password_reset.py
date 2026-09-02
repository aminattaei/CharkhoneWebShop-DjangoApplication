import logging
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction

from .email import build_password_reset_link, send_password_reset_email
from .tokens import generate_reset_token, mark_token_used, verify_reset_token

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class PasswordResetResult:
    ok: bool
    status_code: int
    detail: str


def request_password_reset(email, request):
    try:
        user = User.objects.select_related("profile").get(email=email)
    except User.DoesNotExist:
        logger.info("تلاش بازیابی رمز برای ایمیل ناموجود: %s", email)
        return

    if user.is_locked:
        logger.warning("تلاش بازیابی رمز برای حساب قفل‌شده: %s", email)
        return

    token = generate_reset_token(user)
    reset_link = build_password_reset_link(request, token)
    send_password_reset_email(user, reset_link)
    logger.info("توکن بازیابی رمز برای %s ایجاد شد.", email)


def complete_password_reset(token, new_password):
    user_id = verify_reset_token(token)
    if user_id is None:
        logger.warning("تلاش بازیابی رمز با توکن نامعتبر")
        return PasswordResetResult(
            ok=False,
            status_code=400,
            detail="توکن نامعتبر یا منقضی شده است.",
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("کاربر با شناسه %s یافت نشد.", user_id)
        return PasswordResetResult(
            ok=False,
            status_code=400,
            detail="کاربر یافت نشد.",
        )

    if user.is_locked:
        logger.warning("تلاش تغییر رمز برای حساب قفل‌شده: %s", user.email)
        return PasswordResetResult(
            ok=False,
            status_code=403,
            detail="حساب کاربری قفل شده است.",
        )

    with transaction.atomic():
        token_marked = mark_token_used(token)
        if not token_marked:
            logger.warning("تلاش بازیابی رمز با توکن قبلاً استفاده شده: %s", token[:20])
            return PasswordResetResult(
                ok=False,
                status_code=400,
                detail="توکن قبلاً استفاده شده است.",
            )

        user.set_password(new_password)
        user.failed_reset_attempts = 0
        user.save()

    logger.info("رمز عبور کاربر %s با موفقیت تغییر کرد.", user.email)
    return PasswordResetResult(
        ok=True,
        status_code=200,
        detail="رمز عبور با موفقیت تغییر کرد.",
    )
