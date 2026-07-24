from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import PasswordResetToken


class Command(BaseCommand):
    help = 'حذف توکن‌های بازیابی رمز عبور منقضی‌شده'

    def handle(self, *args, **options):
        now = timezone.now()
        deleted_count, _ = PasswordResetToken.objects.filter(expires_at__lt=now).delete()
        self.stdout.write(
            self.style.SUCCESS(f'تعداد توکن‌های حذف‌شده: {deleted_count}')
        )
