import logging

from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.urls import reverse_lazy

from ..forms import AuthenticationForm

logger = logging.getLogger(__name__)


class LoginView(auth_views.LoginView):
    form_class = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "ورود موفقیت‌آمیز بود!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "ایمیل یا رمز عبور اشتباه است!")
        return super().form_invalid(form)


