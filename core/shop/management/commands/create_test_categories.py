import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from faker import Faker

from shop.models import ProductCategory


class Command(BaseCommand):
    help = "Generate random test categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of categories to create (default: 5)",
        )

        parser.add_argument(
            "-l",
            "--language",
            type=str,
            choices=["en", "fa"],
            default="en",
            help="Language of generated data: en or fa (default: en)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        language = options["language"]

        fake = Faker("fa_IR") if language == "fa" else Faker("en_US")

        created_count = 0

        for i in range(count):
            while True:
                title = fake.word().capitalize() + " " + fake.word().capitalize()
                title = title[:255]

                slug = slugify(
                    title,
                    allow_unicode=True,
                )

                if slug and not ProductCategory.objects.filter(
                    slug=slug
                ).exists():
                    break

            category = ProductCategory.objects.create(
                title=title,
                slug=slug,
            )

            created_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created category #{i + 1}: "
                    f"{category.title} "
                    f"(slug: {category.slug})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {created_count} "
                f"{'Persian' if language == 'fa' else 'English'} "
                f"category(ies)."
            )
        )