"""
URL configuration for shop project.
"""

from django.urls import path, re_path
from . import views

app_name = "shop"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    re_path(
        r"^product/(?P<slug>[\w\-]+)/$",
        views.ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "newsletter/subscribe/",
        views.SubscribeView.as_view(),
        name="newsletter_subscribe",
    ),
    path(
        "newsletter/verify/",
        views.ConfirmSubscriptionView.as_view(),
        name="newsletter_verify",
    ),
    path(
        "newsletter/unsubscribe/",
        views.UnsubscribeView.as_view(),
        name="newsletter_unsubscribe",
    ),
]
