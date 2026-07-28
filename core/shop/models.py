from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

User = get_user_model()


class ProductStatusType(models.IntegerChoices):
    publish = 1, _("publish")
    draft = 2, _("draft")



class ProductCategory(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(allow_unicode=True, unique=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("دسته‌بندی محصول")
        verbose_name_plural = _("دسته‌بندی‌های محصول")

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
    price = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    discount_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")
        ordering = ["-created_date"]

    def __str__(self):
        return self.title

    @property
    def final_price(self):
        if self.discount_percent > 0:
            return self.price * (100 - self.discount_percent) / 100
        return self.price

    @property
    def is_in_stock(self):
        return self.stock > 0


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
        verbose_name = _("تصویر محصول")
        verbose_name_plural = _("تصاویر محصول")

    def __str__(self):
        return f"{self.product.title} - {self.pk}"


