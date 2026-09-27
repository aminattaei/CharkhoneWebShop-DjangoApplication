from django.contrib.auth import forms as auth_forms
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class AuthenticationForm(auth_forms.AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.is_verified:
            raise ValidationError("حساب شما تایید نشده است.")


class RegisterForm(forms.Form):
    email = forms.EmailField(
        label="ایمیل شما",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg text-center",
                "placeholder": "email@site.com",
                "aria-label": "email@site.com",
                "autocomplete": "email",
                "id": "signupSimpleSignupEmail",
            }
        ),
    )
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(
            attrs={
                "class": "js-toggle-password form-control form-control-lg text-center",
                "placeholder": "8+ characters required",
                "aria-label": "8+ characters required",
                "autocomplete": "new-password",
                "id": "signupSimpleSignupPassword",
                "data-hs-toggle-password-options": '{"target": [".js-toggle-password-target-1", ".js-toggle-password-target-2"], "defaultClass": "bi-eye-slash", "showClass": "bi-eye", "classChangeTarget": ".js-toggle-passowrd-show-icon-1"}',
            }
        ),
    )
    password_confirmation = forms.CharField(
        label="رمز عبور را تایید کنید",
        widget=forms.PasswordInput(
            attrs={
                "class": "js-toggle-password form-control form-control-lg text-center",
                "placeholder": "8+ characters required",
                "aria-label": "8+ characters required",
                "autocomplete": "new-password",
                "id": "signupSimpleSignupConfirmPassword",
                "data-hs-validation-equal-field": "#signupSimpleSignupPassword",
                "data-hs-toggle-password-options": '{"target": [".js-toggle-password-target-1", ".js-toggle-password-target-2"], "defaultClass": "bi-eye-slash", "showClass": "bi-eye", "classChangeTarget": ".js-toggle-passowrd-show-icon-2"}',
            }
        ),
    )
    privacy_agreed = forms.BooleanField(
        label="",
        required=True,
        error_messages={"required": "لطفاً سیاست حفظ حریم خصوصی ما را بپذیرید."},
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "signupHeroFormPrivacyCheck",
                "name": "signupFormPrivacyCheck",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise ValidationError("وارد کردن ایمیل الزامی است.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        try:
            validate_password(password)
        except ValidationError as error:
            raise ValidationError(error.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")

        if password and password_confirmation and password != password_confirmation:
            self.add_error(
                "password_confirmation",
                ValidationError("رمز عبور با رمز عبور تأیید مطابقت ندارد."),
            )

        return cleaned_data

