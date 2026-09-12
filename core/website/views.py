from typing import Any

from django.db.models.query import QuerySet
from django.views import generic
from django.db.models import Prefetch


from shop.models import ProductModel,ProductCategory,ProductStatusType

# Create your views here.


class IndexShowView(generic.ListView):
    template_name = "website/index.html"
    context_object_name = "products"

    def get_queryset(self):
        return ProductModel.objects.published()[:3] #type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = ProductCategory.objects.prefetch_related(
            Prefetch(
                "productsـcategory",
                queryset=ProductModel.objects.published(), #type: ignore
                to_attr="category_products",
            )
        )[:3]
        context["categories"] = categories
        return context

class ContactTemplateView(generic.TemplateView):
    template_name = "website/contact.html"


class AboutTemplateView(generic.TemplateView):
    template_name = "website/about.html"
