"""
URL configuration for cart project.
"""

from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("add/", views.CartAddToCartView.as_view(), name="add_to_cart"),
    path("cart-summary/",views.CartSummaryTemplateView.as_view(),name="cart_summary"),
    path(
        "cart/update-quantity/",
        views.update_quantity,
        name="update_quantity",
    ),
    path("checkout/",views.CartCheckoutTemplateView.as_view(),name="cart_chechout"),
]


