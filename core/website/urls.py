from django.urls import path, include

from . import views

app_name = "website"

urlpatterns = [
    path("", views.IndexShowView.as_view(), name="home_page"),
    path("contact/", views.ContactView.as_view(), name="contact_page"),
    path("about/", views.AboutTemplateView.as_view(), name="about_page"),
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
