from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from accounts.services.password_reset import request_password_reset, complete_password_reset


class PasswordResetRequestView(View):
    template_name = "accounts/password_reset_request.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "لطفا ایمیل خود را وارد کنید.")
            return render(request, self.template_name)

        request_password_reset(email, request)
        messages.success(request, "اگر ایمیل وجود داشته باشد، لینک بازیابی رمز عبور ارسال شده است.")
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
