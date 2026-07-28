from django.urls import path

from . import views

app_name = "api-v1"

urlpatterns = [
    path('request-reset/', views.RequestPasswordReset.as_view(), name='request-reset'),
    path('reset-password/', views.ResetPassword.as_view(), name='reset-password'),
]
