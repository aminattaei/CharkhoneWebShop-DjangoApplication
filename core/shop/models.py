from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

from django.db.models.functions import Cast


from django.utils import timezone
from datetime import timedelta

from decimal import Decimal

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

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_date"]

    def __str__(self):
        return self.title


    @property
    def final_price(self):
        if not hasattr(self, 'price') or self.price is None:
            return Decimal(0)
        
        if not isinstance(self.price, (int, float)):
            try:
                price_value = float(self.price)
            except (ValueError, TypeError):
                return Decimal(0)
        else:
            price_value = self.price
        
        if not hasattr(self, 'discount_percent') or self.discount_percent is None:
            discount_value = 0
        elif not isinstance(self.discount_percent, (int, float)):
            try:
                discount_value = float(self.discount_percent)
            except (ValueError, TypeError):
                discount_value = 0
        else:
            discount_value = self.discount_percent
        
        discount = Decimal(max(0, min(100, discount_value)))
        price = Decimal(str(price_value))
        
        final = int(price * (100 - discount) / 100)
        
        return final


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
