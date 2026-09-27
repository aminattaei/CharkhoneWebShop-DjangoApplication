from django.urls import path, include
from django.contrib.auth.views import LogoutView

from . import views

app_name = "accounts"


urlpatterns = [
    path('register/',views.RegisterView.as_view(),name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password_reset/", views.PasswordResetRequestView.as_view(), name="password_reset"),
    path("password_reset/done/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("verify-email/", views.RequestVerificationView.as_view(), name="verify-email"),
    path("verify-email/sent/", views.ResendVerificationView.as_view(), name="verify-email-sent"),
    path("verify-email/confirm/", views.ConfirmVerificationView.as_view(), name="verify-email-confirm"),
    path("api/v1/", include("accounts.api.v1.urls")),
    path("reset-password/", views.ResetPasswordPage.as_view(), name="reset-password-page"),
]
