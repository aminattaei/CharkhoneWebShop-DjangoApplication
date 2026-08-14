from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView



class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/passwod_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class ResetPasswordPage(TemplateView):
    template_name = "accounts/reset_password_confirm.html"
