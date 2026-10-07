from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView
from django.core.cache import cache
from django.db import transaction

from accounts.services.password_reset import (
    request_password_reset,
    complete_password_reset,
)

RESET_RATE_LIMIT_KEY = "password_reset_rate_limit_{email}"
RESET_RATE_LIMIT_MAX = 3
RESET_RATE_LIMIT_DURATION = 3600


class PasswordResetRequestView(View):
    template_name = "accounts/password_reset_request.html"

    def get(self, request):
        return render(request, self.template_name)

    @transaction.atomic
    def post(self, request):
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "لطفا ایمیل خود را وارد کنید.")
            return render(request, self.template_name)

        cache_key = RESET_RATE_LIMIT_KEY.format(email=email.lower())
        current_count = cache.get(cache_key, 0)

        if current_count >= RESET_RATE_LIMIT_MAX:
            messages.error(
                request,
                "تعداد درخواست‌های بازیابی رمز عبور بیش از حد مجاز است. "
                "لطفا بعداً تلاش کنید.",
            )
            return render(request, self.template_name)

        request_password_reset(email, request)
        cache.set(cache_key, current_count + 1, RESET_RATE_LIMIT_DURATION)
        messages.success(
            request,
            "اگر ایمیل وجود داشته باشد، لینک بازیابی رمز عبور ارسال شده است.",
        )
        return redirect("accounts:password_reset_done")


class PasswordResetConfirmView(View):
    template_name = "accounts/password_reset_confirm_custom.html"

    def get(self, request, token):
        if not token:
            messages.error(request, "توکن بازیابی نامعتبر است.")
            return redirect("accounts:login")

        return render(request, self.template_name, {"token": token})

    def post(self, request, token):
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not password or not confirm_password:
            messages.error(request, "لطفا تمام فیلدها را پر کنید.")
            return render(request, self.template_name, {"token": token})

        if password != confirm_password:
            messages.error(request, "رمز عبور و تکرار آن مطابقت ندارند.")
            return render(request, self.template_name, {"token": token})

        result = complete_password_reset(token, password)
        if result.ok:
            messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")
            return redirect("accounts:login")
        else:
            messages.error(request, result.detail)
            return render(request, self.template_name, {"token": token})


class PasswordResetDoneView(TemplateView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetCompleteView(TemplateView):
    template_name = "accounts/password_reset_complete.html"


class ResetPasswordPage(TemplateView):
    template_name = "accounts/reset_password_confirm.html"
