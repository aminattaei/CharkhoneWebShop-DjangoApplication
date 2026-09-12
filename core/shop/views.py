from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import generic, View
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction

from .filters import apply_product_filters
from .forms import SubscriberForm
from .models import ProductCategory, ProductModel, Subscriber


class ProductListView(generic.ListView):
    model = ProductModel
    template_name = "shop/product-grid.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            ProductModel.objects.published() #type: ignore
            .select_related("category", "user")
            .order_by("-created_date")
        )
        return apply_product_filters(queryset, self.request.GET)

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get("page_size", "")
        if page_size.isdigit() and 0 < int(page_size) <= 50:
            return int(page_size)
        return self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ProductCategory.objects.all()
        return context


class ProductDetailView(generic.DetailView):
    model = ProductModel
    context_object_name = "product"
    template_name = "shop/product-details.html"

    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        if slug is None:
            raise Http404("محصول یافت نشد")

        return get_object_or_404(
            ProductModel.objects.prefetch_related("product_images"),
            slug=slug
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object #type: ignore
        context["images"] = product.product_images.all()
        return context


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
                raw_token = f"newsletter:{subscriber.id}:{timezone.now().timestamp()}"
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
            raw_token = signer.unsign(token, max_age=NEWSLETTER_VERIFICATION_MAX_AGE)
        except (BadSignature, SignatureExpired):
            messages.error(request, "توکن تایید نامعتبر یا منقضی شده است.")
            return redirect("website:home_page")

        token_hash = hash_token(raw_token)
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
    return f"{base_url}/shop/newsletter/verify/?token={token}"


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