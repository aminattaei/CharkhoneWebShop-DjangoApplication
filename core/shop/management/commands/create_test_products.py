import os
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from faker import Faker

from shop.models import (
    ProductCategory,
    ProductImageModel,
    ProductModel,
    ProductStatusType,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Generate random test products"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of products to create (default: 10)",
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

        # ---------------------------------------------------------
        # Load images
        # ---------------------------------------------------------

        main_images_dir = os.path.join(
            settings.MEDIA_ROOT,
            "product",
            "images",
        )

        extra_images_dir = os.path.join(
            settings.MEDIA_ROOT,
            "product",
            "extra-img",
        )

        main_images = []
        extra_images = []

        if os.path.exists(main_images_dir):
            for filename in os.listdir(main_images_dir):
                if filename.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif")
                ):
                    main_images.append(
                        f"product/images/{filename}"
                    )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Main images directory not found: "
                    f"{main_images_dir}. Using default."
                )
            )

        if os.path.exists(extra_images_dir):
            for filename in os.listdir(extra_images_dir):
                if filename.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif")
                ):
                    extra_images.append(
                        f"product/extra-img/{filename}"
                    )

        if not main_images:
            main_images = [
                "defaults/default_image.png"
            ]

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(main_images)} main image(s) "
                f"and {len(extra_images)} extra image(s)"
            )
        )

        # ---------------------------------------------------------
        # Load categories
        # ---------------------------------------------------------

        categories = list(ProductCategory.objects.all())

        if not categories:
            raise CommandError(
                "No categories found. "
                "Run 'python manage.py create_test_categories' "
                "first."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(categories)} category(s)"
            )
        )

        # ---------------------------------------------------------
        # Ensure at least one user exists
        # ---------------------------------------------------------

        users = list(User.objects.all())

        if not users:
            self.stdout.write(
                self.style.WARNING(
                    "No users found. Creating a default admin user..."
                )
            )

            admin_user = User.objects.create_superuser(
                email="admin@example.com",
                password="admin123",
            )

            users.append(admin_user)

            self.stdout.write(
                self.style.SUCCESS(
                    "Created default admin user"
                )
            )

        # ---------------------------------------------------------
        # Generate products
        # ---------------------------------------------------------

        created_count = 0

        for i in range(count):

            # Generate unique title and slug
            while True:
                title = fake.sentence(
                    nb_words=3,
                    variable_nb_words=True,
                )[:255]

                slug = slugify(
                    title,
                    allow_unicode=True,
                )

                if slug and not ProductModel.objects.filter(
                    slug=slug
                ).exists():
                    break

            # Random data
            user = random.choice(users)
            category = random.choice(categories)
            random_main_image = random.choice(main_images)

            # Create product
            product = ProductModel.objects.create(
                user=user,
                category=category,
                title=title,
                slug=slug,
                image=random_main_image,
                description=fake.text(
                    max_nb_chars=500
                ),
                brief_description=fake.text(
                    max_nb_chars=100
                ),
                stock=random.randint(0, 100),
                status=random.choice(
                    [
                        ProductStatusType.publish,
                        ProductStatusType.draft,
                    ]
                ),
                price=random.randint(
                    10000,
                    1000000,
                ),
                discount_percent=random.randint(
                    0,
                    50,
                ),
            )

            created_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created product #{i + 1}: "
                    f"{product.title} "
                    f"(slug: {product.slug})"
                )
            )

            # -----------------------------------------------------
            # Extra product images
            # -----------------------------------------------------

            if extra_images:
                if random.choice([True, False]):
                    num_extra_images = random.randint(
                        1,
                        min(3, len(extra_images)),
                    )

                    for _ in range(num_extra_images):
                        random_extra_image = random.choice(
                            extra_images
                        )

                        ProductImageModel.objects.create(
                            product=product,
                            file=random_extra_image,
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  → Added {num_extra_images} "
                            f"extra image(s) for "
                            f"'{product.title}'"
                        )
                    )

            else:
                # Fallback to main images
                if random.choice([True, False]):
                    num_extra_images = random.randint(1, 3)

                    for _ in range(num_extra_images):
                        random_extra_image = random.choice(
                            main_images
                        )

                        ProductImageModel.objects.create(
                            product=product,
                            file=random_extra_image,
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  → Added {num_extra_images} "
                            f"extra image(s) from main images "
                            f"for '{product.title}'"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {created_count} "
                f"{'Persian' if language == 'fa' else 'English'} "
                f"product(s)."
            )
        )