from django.db.models.query import QuerySet
from django.views import generic
from django.db.models import Prefetch
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import ContactForm


from shop.models import ProductModel, ProductCategory, ProductStatusType

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
