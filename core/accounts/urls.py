from django.urls import path

from . import views

app_name = "accounts"

from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('password_reset/', views.PasswordResetView.as_view(), name="password_reset"),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path('reset-password/', views.ResetPasswordPage.as_view(), name='reset-password-page'),
    path('api/request-reset/', views.RequestPasswordReset.as_view(), name='request-reset'),
    path('api/reset-password/', views.ResetPassword.as_view(), name='reset-password'),
]
