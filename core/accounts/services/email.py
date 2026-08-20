import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def build_password_reset_link(request, token):
    protocol = "https" if request.is_secure() else "http"
    domain = request.get_host()
    return f"{protocol}://{domain}/accounts/reset-password/?token={token}"


def send_password_reset_email(user, reset_link):
    email = user.email
    try:
        send_mail(
            subject="بازیابی رمز عبور",
            message=(
                f"سلام {user.profile.first_name or user.email},\n\n"
                f"برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:\n\n"
                f"{reset_link}\n\n"
                f"اگر شما درخواست بازیابی رمز نداده‌اید، این ایمیل را نادیده بگیرید."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("ایمیل بازیابی رمز عبور با موفقیت به %s ارسال شد.", email)
    except Exception as e:
        logger.error("خطا در ارسال ایمیل به %s: %s", email, e)