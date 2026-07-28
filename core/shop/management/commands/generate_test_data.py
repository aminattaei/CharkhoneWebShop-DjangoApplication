import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker
from shop.models import ProductModel, ProductCategory, ProductImageModel, ProductStatusType
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Generate fake products for the shop app"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="Number of products to create (default: 20)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        fake = Faker()

        # --- Ensure categories exist ---
        categories = list(ProductCategory.objects.all())
        if not categories:
            self.stdout.write(
                self.style.WARNING("No categories found. Creating default categories...")
            )
            default_categories = [
                "Electronics",
                "Books",
                "Clothing",
                "Home & Kitchen",
                "Sports",
                "Toys",
                "Beauty",
                "Automotive",
                "Health",
                "Garden",
            ]
            for cat in default_categories:
                slug = slugify(cat, allow_unicode=True)
                category, created = ProductCategory.objects.get_or_create(
                    slug=slug, defaults={"title": cat}
                )
                categories.append(category)
            self.stdout.write(
                self.style.SUCCESS(f"Created {len(default_categories)} categories")
            )

        # --- Ensure at least one user exists ---
        users = list(User.objects.all())
        if not users:
            self.stdout.write(
                self.style.WARNING("No users found. Creating a default admin user...")
            )
            admin_user = User.objects.create_superuser(
                username=None, #type: ignore
                email="admin@example.com", password="admin123"
            )
            users.append(admin_user)
            self.stdout.write(self.style.SUCCESS("Created default admin user"))

        # --- Generate products ---
        created_count = 0
        for i in range(count):
            # Generate unique title and slug
            title = fake.sentence(nb_words=3, variable_nb_words=True)[:255]
            slug = slugify(title, allow_unicode=True)
            while ProductModel.objects.filter(slug=slug).exists():
                title = fake.sentence(nb_words=3, variable_nb_words=True)[:255]
                slug = slugify(title, allow_unicode=True)

            # Randomly pick user and category
            user = random.choice(users)
            category = random.choice(categories)

            # Create product
            product = ProductModel.objects.create(
                user=user,
                category=category,
                title=title,
                slug=slug,
                image="defaults/default_image.png",  # using default image
                description=fake.text(max_nb_chars=500),
                brief_description=fake.text(max_nb_chars=100),
                stock=random.randint(0, 100),
                status=random.choice([ProductStatusType.publish, ProductStatusType.draft]),
                price=random.randint(10000, 1000000),
                discount_percent=random.randint(0, 50),
            )
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created product #{i+1}: {product.title} (slug: {product.slug})"
                )
            )

            # Optionally create extra product images (1–3)
            if random.choice([True, False]):
                num_extra_images = random.randint(1, 3)
                for _ in range(num_extra_images):
                    ProductImageModel.objects.create(
                        product=product,
                        file="defaults/default_image.png",  # using default image
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  → Added {num_extra_images} extra image(s) for '{product.title}'"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Successfully generated {created_count} product(s) with categories and extra images."
            )
        )