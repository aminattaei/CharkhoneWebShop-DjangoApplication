from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.password_reset import (
    complete_password_reset,
    request_password_reset,
)
from accounts.throttles import (
    ResetRequestThrottle,
    ResetAttemptThrottle,
    EmailBasedThrottle,
)

from .serializers import ResetRequestSerializer, ResetPasswordSerializer


class RequestPasswordReset(APIView):
    throttle_classes = [ResetRequestThrottle, EmailBasedThrottle]

    def post(self, request):
        serializer = ResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(
            email=serializer.validated_data["email"],
            request=request,
        )

        return Response(
            {"detail": "در صورت وجود ایمیل، لینک بازیابی ارسال شد."},
            status=status.HTTP_200_OK,
        )


class ResetPassword(APIView):
    throttle_classes = [ResetAttemptThrottle]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = complete_password_reset(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )

        return Response({"detail": result.detail}, status=result.status_code)