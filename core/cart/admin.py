from django.contrib import admin

from .models import Cart, CartItem


# Register your models here.



@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_date",
        "updated_date",
    )

    list_filter = (
        "created_date",
        "updated_date",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = (
        "-created_date",
    )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "product",
        "quantity",
        "created_date",
        "updated_date",
    )

    list_filter = (
        "created_date",
        "updated_date",
    )

    search_fields = (
        "cart__user__username",
        "cart__user__email",
        "product__name",
    )

    ordering = (
        "-created_date",
    )