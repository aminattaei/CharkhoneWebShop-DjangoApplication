from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from shop.models import ProductModel

User = get_user_model()


class Cart(models.Model):
    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.CASCADE)

    created_date = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True, auto_now_add=False)
    

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self):
        return (f"Cart for {self.user} / created at: {self.created_date}")

    def get_absolute_url(self):
        return reverse("Cart_detail", kwargs={"pk": self.pk})


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(ProductModel, related_name='cart_items', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default = 0)

    created_date = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name = _("CartItem")
        verbose_name_plural = _("CartItems")

    def __str__(self):
        return (f"Cart for {self.cart} / created at: {self.created_date}")

    def get_absolute_url(self):
        return reverse("CartItem_detail", kwargs={"pk": self.pk})
