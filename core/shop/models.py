from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

from django.utils import timezone
from datetime import timedelta

from .managers import ProductQuerySet
from .services import calculate_final_price

User = get_user_model()


class ProductStatusType(models.IntegerChoices):
    publish = 1, _("نمایش")
    draft = 2, _("عدم نمایش")


class ProductCategory(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(allow_unicode=True, unique=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.title


class ProductModel(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="products",
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="products",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(allow_unicode=True, unique=True)
    image = models.ImageField(
        default="defaults/default_image.png",
        upload_to="product/img/",
    )
    description = models.TextField()
    brief_description = models.TextField()
    stock = models.PositiveIntegerField(default=0)
    status = models.IntegerField(
        choices=ProductStatusType.choices,
        default=ProductStatusType.publish,
    )
    price = models.DecimalField(max_digits=15, decimal_places=0, default=0)  # type: ignore
    discount_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_date"]

    def __str__(self):
        return self.title

    @property
    def final_price(self):
        return calculate_final_price(self.price, self.discount_percent)

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def is_new(self):
        return self.created_date > timezone.now() - timedelta(days=10)


class ProductImageModel(models.Model):
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="product_images",
    )
    file = models.ImageField(upload_to="product/extra-img/")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        return f"{self.product.title} - {self.pk}"