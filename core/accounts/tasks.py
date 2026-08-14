import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from accounts.services.email import send_password_reset_email

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_reset_email_task(self, user_id, reset_link):
    try:
        user = User.objects.select_related("profile").get(id=user_id)
        send_password_reset_email(user, reset_link)
    except User.DoesNotExist:
        logger.error("کاربر با شناسه %s یافت نشد.", user_id)
    except Exception as exc:
        logger.error("خطا در ارسال ایمیل به کاربر %s: %s", user_id, exc)
        self.retry(exc=exc, countdown=60)