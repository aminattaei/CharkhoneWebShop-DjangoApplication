# accounts/views.py
import logging
from django.conf import settings as django_settings
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .forms import AuthenticationForm
from .serializers import RequestPasswordResetSerializer, ResetPasswordSerializer
from .utils import (
    generate_password_reset_token,
    verify_password_reset_token,
    mark_token_as_used,
    cleanup_expired_tokens,
)

User = get_user_model()
logger = logging.getLogger(__name__)

PASSWORD_RESET_LINK_BASE = getattr(django_settings, 'PASSWORD_RESET_LINK_BASE', 'http://localhost:3000/reset-password')
DEFAULT_FROM_EMAIL = getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')


class LoginView(auth_views.LoginView):
    form_class = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "ورود موفقیت‌آمیز بود!")
        cleanup_expired_tokens()
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "ایمیل یا رمز عبور اشتباه است!")
        return super().form_invalid(form)


class RequestPasswordReset(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()
        if user:
            token = generate_password_reset_token(user)
            reset_link = f"{PASSWORD_RESET_LINK_BASE}?token={token}"
            try:
                send_mail(
                    subject='بازیابی رمز عبور',
                    message=(
                        f'برای بازیابی رمز عبور روی لینک زیر کلیک کنید:\n'
                        f'{reset_link}\n\n'
                        f'این لینک تا ۴۸ ساعت معتبر است.'
                    ),
                    from_email=DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                logger.info("Password reset email sent to %s", email)
            except Exception as e:
                logger.error("Failed to send password reset email to %s: %s", email, e)
                return Response(
                    {'error': 'خطا در ارسال ایمیل. لطفاً دوباره تلاش کنید.'},
                    status=500,
                )

        return Response({
            'message': 'در صورت وجود ایمیل، لینک بازیابی ارسال شد.'
        })


class ResetPassword(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            validate_password(new_password)
        except ValidationError as e:
            return Response(
                {'error': 'رمز عبور ضعیف است.', 'details': e.messages},
                status=400,
            )

        user_id = verify_password_reset_token(token)
        if not user_id:
            return Response(
                {'error': 'توکن نامعتبر یا منقضی شده است.'},
                status=400,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'کاربر یافت نشد.'},
                status=404,
            )

        user.set_password(new_password)
        user.save()
        mark_token_as_used(token)
        logger.info("Password reset completed for user %s", user.email)

        return Response({'message': 'رمز عبور با موفقیت تغییر یافت.'})