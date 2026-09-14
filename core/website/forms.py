from django import forms
from .models import ContactModel


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactModel
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام و نام خانوادگی"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "ایمیل شما"}
            ),
            "subject": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "موضوع پیام"}
            ),
            "message": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "متن پیام...", "rows": 5}
            ),
        }
        error_messages = {
            "name": {"required": "لطفاً نام خود را وارد کنید."},
            "email": {
                "required": "لطفاً ایمیل خود را وارد کنید.",
                "invalid": "ایمیل وارد شده معتبر نیست.",
            },
            "subject": {"required": "لطفاً موضوع را وارد کنید."},
            "message": {"required": "لطفاً متن پیام را وارد کنید."},
        }
