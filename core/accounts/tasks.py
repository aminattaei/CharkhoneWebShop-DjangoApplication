import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_reset_email_task(self, email, reset_link):
    try:
        send_mail(
            subject='بازیابی رمز عبور',
            message=f'برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:\n\n{reset_link}\n\nاین لینک تا ۴۸ ساعت معتبر است.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("ایمیل بازیابی رمز عبور با موفقیت به %s ارسال شد.", email)
    except Exception as exc:
        logger.error("خطا در ارسال ایمیل به %s: %s", email, exc)
        self.retry(exc=exc, countdown=60)
