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

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create a cart for the given user."""
        cart, created = cls.objects.get_or_create(user=user)
        return cart

    def add_item(self, product_id, quantity=1):
        """Add or update an item in the cart."""
        cart_item, created = self.line_items.get_or_create(
            product_id=product_id,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        return cart_item

    def merge_session_cart(self, session_cart):
        """Merge session cart items into this user's cart."""
        for item in session_cart.items:
            self.add_item(item["product_id"], item["quantity"])
        session_cart.clear()

    @property
    def items(self):
        """Return list of dicts with product_id and quantity for compatibility with CartSession."""
        return [
            {"product_id": str(item.product_id), "quantity": item.quantity}
            for item in self.line_items.all()
        ]

    @property
    def total_items(self):
        return sum(item.quantity for item in self.line_items.all())

    @property
    def total_price(self):
        total = 0
        for item in self.line_items.all():
            if item.product:
                total += item.product.final_price * item.quantity
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='line_items', on_delete=models.CASCADE)
    product = models.ForeignKey(ProductModel, related_name='cart_items', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)

    created_date = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name = _("CartItem")
        verbose_name_plural = _("CartItems")

    def __str__(self):
        return (f"Cart for {self.cart} / created at: {self.created_date}")

    def get_absolute_url(self):
        return reverse("CartItem_detail", kwargs={"pk": self.pk})