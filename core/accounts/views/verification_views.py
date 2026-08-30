from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from django.views import View

from accounts.models import EmailVerificationToken
from accounts.services.verification import (
    build_verification_link,
    mark_verification_token_used,
    send_verification_email,
    verify_verification_token,
    generate_verification_token,
)

User = get_user_model()


class RequestVerificationView(View):
    template_name = "accounts/verify_email.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "لطفا ایمیل خود را وارد کنید.")
            return render(request, self.template_name)

        user = User.objects.filter(email=email).first()
        if user and not user.is_verified:
            token = build_verification_link(request, generate_verification_token(user))
            send_verification_email(user, token)

        messages.success(request, "اگر ایمیل وجود داشته باشد، لینک تایید ارسال شده است.")
        return redirect("accounts:verify_email_sent")


class ConfirmVerificationView(View):
    template_name = "accounts/verify_email_confirm.html"

    def get(self, request, token=None):
        token = token or request.GET.get("token", "")
        if not token:
            messages.error(request, "توکن تایید نامعتبر است.")
            return redirect("accounts:login")

        user_id = verify_verification_token(token)
        if user_id is None:
            messages.error(request, "توکن تایید نامعتبر یا منقضی شده است.")
            return redirect("accounts:login")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "کاربر پیدا نشد.")
            return redirect("accounts:login")

        if user.is_verified:
            messages.info(request, "حساب شما قبلاً تایید شده است.")
            return redirect("accounts:login")

        user.is_verified = True
        user.is_active = True
        user.deactivated_at = None
        user.save(update_fields=["is_verified", "is_active", "deactivated_at", "updated_date"])
        mark_verification_token_used(token)
        messages.success(request, "حساب شما با موفقیت تایید شد.")
        return redirect("accounts:login")

    def post(self, request):
        return redirect("accounts:login")


class ResendVerificationView(View):
    template_name = "accounts/verify_email.html"
    sent_template_name = "accounts/verify_email_sent.html"

    def get(self, request):
        return render(request, self.sent_template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "لطفا ایمیل خود را وارد کنید.")
            return render(request, self.template_name)

        user = User.objects.filter(email=email).first()
        if user and not user.is_verified:
            token = build_verification_link(request, generate_verification_token(user))
            send_verification_email(user, token)

        messages.success(request, "اگر ایمیل وجود داشته باشد، لینک تایید مجددا ارسال شده است.")
        return redirect("accounts:verify_email_sent")