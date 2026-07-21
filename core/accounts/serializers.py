from rest_framework import serializers


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, error_messages={
        'required': 'ایمیل الزامی است.',
        'invalid': 'فرمت ایمیل نادرست است.',
    })


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, error_messages={
        'required': 'توکن الزامی است.',
    })
    new_password = serializers.CharField(required=True, min_length=8, error_messages={
        'required': 'رمز عبور جدید الزامی است.',
        'min_length': 'رمز عبور باید حداقل ۸ کاراکتر باشد.',
    })
