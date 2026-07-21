from django.core.management.base import BaseCommand
from accounts.utils import cleanup_expired_tokens


class Command(BaseCommand):
    help = 'حذف توکن‌های منقضی شده بازیابی رمز عبور'

    def handle(self, *args, **options):
        deleted = cleanup_expired_tokens()
        self.stdout.write(
            self.style.SUCCESS(f'{deleted} توکن منقضی شده حذف شد.')
        )
