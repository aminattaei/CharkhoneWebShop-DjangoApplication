import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.services import (
    generate_reset_token,
    send_reset_email,
    build_password_reset_link,
    complete_password_reset,
)
from accounts.throttles import (
    ResetRequestThrottle,
    ResetAttemptThrottle,
    EmailBasedThrottle,
)

from .serializers import ResetRequestSerializer, ResetPasswordSerializer

logger = logging.getLogger(__name__)


class RequestPasswordReset(APIView):
    throttle_classes = [ResetRequestThrottle, EmailBasedThrottle]

    def post(self, request):
        serializer = ResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.select_related("profile").get(email=email)
            if user.is_locked:
                logger.warning("تلاش بازیابی رمز برای حساب قفل‌شده: %s", email)
            else:
                token = generate_reset_token(user)
                reset_link = build_password_reset_link(request, token)
                send_reset_email(user, reset_link)
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

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        # complete_password_reset claims the token under a row lock and changes
        # the password in the same transaction, so one token can be spent only
        # once even under concurrent requests.
        result = complete_password_reset(token, new_password)

        return Response({"detail": result.detail}, status=result.status_code)
