import logging

from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.views import View
from django.shortcuts import render, redirect

from ..forms import AuthenticationForm, RegisterForm
from ..services.verification import (
    build_verification_link,
    generate_verification_token,
    send_verification_email,
)
from cart.cart import CartSession
from cart.models import Cart

User = get_user_model()

logger = logging.getLogger(__name__)


def merge_session_cart_to_user(request, user):
    """Merge session cart into user's persistent cart."""
    session_cart = CartSession(request.session)
    if session_cart.items:
        user_cart = Cart.get_or_create_for_user(user)
        user_cart.merge_session_cart(session_cart)


class LoginView(auth_views.LoginView):
    form_class = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        merge_session_cart_to_user(self.request, self.request.user)
        messages.success(self.request, "ورود موفقیت‌آمیز بود!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "ایمیل یا رمز عبور اشتباه است!")
        return super().form_invalid(form)


class RegisterView(View):
    template_name = "accounts/register.html"

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        context = {"form": form}

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # User and verification token are persisted together; the email is
            # only sent once that transaction has committed, so a rollback can
            # never leave a delivered link pointing at a missing account.
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                )
                # Only a hash of this token is stored, so the signed token is
                # kept in memory and emailed after the commit.
                verification_token = generate_verification_token(user)

            verification_sent = send_verification_email(
                user, build_verification_link(request, verification_token)
            )

            # Log the user in automatically after registration
            login(request, user)
            
            # Merge session cart to user's cart
            merge_session_cart_to_user(request, user)

            if verification_sent:
                messages.success(
                    request,
                    "ثبت نام شما با موفقیت انجام شد. لطفاً ایمیل خود را بررسی کنید.",
                )
            else:
                messages.warning(
                    request,
                    "ثبت نام انجام شد، اما ارسال ایمیل تایید ممکن نشد. "
                    "لطفاً از صفحه ارسال مجدد ایمیل تایید استفاده کنید.",
                )
            return redirect("accounts:login")

        return render(request, self.template_name, context)
