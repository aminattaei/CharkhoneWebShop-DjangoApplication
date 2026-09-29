"""
URL configuration for cart project.
"""

from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("add/", views.AddToCartView.as_view(), name="add_to_cart"),
]


