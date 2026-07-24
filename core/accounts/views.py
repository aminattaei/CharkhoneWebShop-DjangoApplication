# accounts/views.py
import logging

from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import AuthenticationForm
from .models import User
from .serializers import ResetRequestSerializer, ResetPasswordSerializer
from .services import generate_reset_token, verify_reset_token, mark_token_used, send_reset_email
from .throttles import ResetRequestThrottle, ResetAttemptThrottle, EmailBasedThrottle

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


class RequestPasswordReset(APIView):
    throttle_classes = [ResetRequestThrottle, EmailBasedThrottle]

    def post(self, request):
        serializer = ResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.select_related('profile').get(email=email)
            if user.is_locked:
                logger.warning("تلاش بازیابی رمز برای حساب قفل‌شده: %s", email)
            else:
                token = generate_reset_token(user)
                send_reset_email(user, token, request)
                logger.info("توکن بازیابی رمز برای %s ایجاد شد.", email)
        except User.DoesNotExist:
            logger.info("تلاش بازیابی رمز برای ایمیل ناموجود: %s", email)

        return Response(
            {"detail": "در صورت وجود ایمیل، لینک بازیابی ارسال شد."},
            status=status.HTTP_200_OK,
        )


class ResetPassword(APIView):
    throttle_classes = [ResetAttemptThrottle]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        user_id = verify_reset_token(token)
        if user_id is None:
            logger.warning("تلاش بازیابی رمز با توکن نامعتبر")
            return Response(
                {"detail": "توکن نامعتبر یا منقضی شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error("کاربر با شناسه %s یافت نشد.", user_id)
            return Response(
                {"detail": "کاربر یافت نشد."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_locked:
            logger.warning("تلاش تغییر رمز برای حساب قفل‌شده: %s", user.email)
            return Response(
                {"detail": "حساب کاربری قفل شده است."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.set_password(new_password)
        user.failed_reset_attempts = 0
        user.save()

        mark_token_used(token)
        logger.info("رمز عبور کاربر %s با موفقیت تغییر کرد.", user.email)

        return Response(
            {"detail": "رمز عبور با موفقیت تغییر کرد."},
            status=status.HTTP_200_OK,
        )
