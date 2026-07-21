from django.urls import path

from . import views

app_name = "accounts"

from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('request-reset/', views.RequestPasswordReset.as_view(), name="request-reset"),
    path('reset-password/', views.ResetPassword.as_view(), name="reset-password"),
]
