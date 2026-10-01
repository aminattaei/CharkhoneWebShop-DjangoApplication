from django.db.models.query import QuerySet
from django.views import generic,View
from django.db.models import Prefetch
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.shortcuts import redirect
from datetime import datetime


from .forms import ContactForm,SubscriberForm
from .services import NewsletterService

from shop.models import (
    ProductModel, ProductCategory, ProductStatusType,
)

from .models import Subscriber, Newsletter, NewsletterRecipient

# Create your views here.


class IndexShowView(generic.ListView):
    template_name = "website/index.html"
    context_object_name = "products"

    def get_queryset(self):
        return ProductModel.objects.published()[:3]  # type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = ProductCategory.objects.prefetch_related(
            Prefetch(
                "productsـcategory",
                queryset=ProductModel.objects.published(),  # type: ignore
                to_attr="category_products",
            )
        )[:3]
        context["categories"] = categories
        return context


class ContactView(generic.FormView):
    template_name = "website/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("website:contact_page")

    def form_valid(self, form):
        contact = form.save()

        try:
            html_message = render_to_string(
                "contact/email/admin_notification.html",
                {
                    "contact": contact,
                },
            )
            plain_message = strip_tags(html_message)

            send_mail(
                subject=f"پیام جدید: {contact.subject}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                html_message=html_message,
                fail_silently=False,
            )

            messages.success(self.request, "پیام شما با موفقیت ارسال شد.")
        except Exception:
            messages.warning(
                self.request, "پیام ثبت شد اما در ارسال ایمیل مشکلی پیش آمد."
            )

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "لطفاً خطاهای فرم را برطرف کنید.")
        return super().form_invalid(form)


class AboutTemplateView(generic.TemplateView):
    template_name = "website/about.html"




signer = TimestampSigner()
NEWSLETTER_VERIFICATION_MAX_AGE = 12 * 3600


class SubscribeView(View):
    def post(self, request):
        form = SubscriberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            subscriber, created = Subscriber.objects.get_or_create(
                email=email,
                defaults={"is_active": True},
            )

            if not created:
                if not subscriber.is_active:
                    subscriber.is_active = True
                    subscriber.save(update_fields=["is_active"])
                    messages.success(request, "اشتراک شما دوباره فعال شد.")
                elif subscriber.is_verified:
                    messages.info(request, "شما قبلاً عضو خبرنامه شده اید.")
                else:
                    messages.info(request, "لینک تایید قبلاً ارسال شده است.")
            else:
                raw_token = f"newsletter:{subscriber.pk}:{datetime.now().timestamp()}"
                signed_token = signer.sign(raw_token)
                subscriber.verification_token = hash_token(signed_token)
                subscriber.save(update_fields=["verification_token"])

                link = build_newsletter_verification_link(request, signed_token)
                send_newsletter_verification_email(request, subscriber, link)
                messages.success(request, "لینک تایید به ایمیل شما ارسال شد.")

            return redirect("website:home_page")

        messages.error(request, "لطفا ایمیل معتبر وارد کنید.")
        return redirect("website:home_page")


class ConfirmSubscriptionView(View):
    def get(self, request):
        token = request.GET.get("token", "")
        if not token:
            messages.error(request, "توکن تایید نامعتبر است.")
            return redirect("website:home_page")

        try:
            signer.unsign(token, max_age=NEWSLETTER_VERIFICATION_MAX_AGE)
        except (BadSignature, SignatureExpired):
            messages.error(request, "توکن تایید نامعتبر یا منقضی شده است.")
            return redirect("website:home_page")

        # The database stores the hash of the *signed* token (see SubscribeView),
        # so the lookup must hash the signed token exactly as it was emailed.
        token_hash = hash_token(token)
        try:
            subscriber = Subscriber.objects.get(verification_token=token_hash)
        except Subscriber.DoesNotExist:
            messages.error(request, "عضویت پیدا نشد.")
            return redirect("website:home_page")

        if subscriber.is_verified:
            messages.info(request, "عضویت شما قبلاً تایید شده است.")
            return redirect("website:home_page")

        subscriber.is_verified = True
        subscriber.save(update_fields=["is_verified"])
        messages.success(request, "عضویت شما در خبرنامه با موفقیت تایید شد.")
        return redirect("website:home_page")


class UnsubscribeView(View):
    def get(self, request):
        email = request.GET.get("email", "")
        if not email:
            messages.error(request, "آدرس ایمیل نامعتبر است.")
            return redirect("website:home_page")

        subscriber = Subscriber.objects.filter(email=email).first()
        if subscriber and subscriber.is_active:
            subscriber.unsubscribe()
            messages.success(request, "اشتراک شما با موفقیت لغو شد.")
        else:
            messages.info(request, "اشتراک فعالی با این ایمیل پیدا نشد.")

        return redirect("website:home_page")


def hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def build_newsletter_verification_link(request, token):
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}/newsletter/verify/?token={token}"


def send_newsletter_verification_email(request, subscriber, link):
    try:
        send_mail(
            subject="تایید عضویت در خبرنامه",
            message=(
                "برای تایید عضویت خود در خبرنامه روی لینک زیر کلیک کنید:\n\n"
                f"{link}\n\n"
                "اگر شما درخواست عضویت نداده‌اید، این ایمیل را نادیده بگیرید."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscriber.email],
            fail_silently=False,
        )
    except Exception as e:
        messages.error(request, f"خطا در ارسال ایمیل: {e}")