from django.views import generic

from .filters import apply_product_filters
from .models import ProductCategory, ProductModel


class ProductListView(generic.ListView):
    model = ProductModel
    template_name = "shop/product-grid.html"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            ProductModel.objects.published()
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

    def get_queryset(self):
        return ProductModel.objects.prefetch_related("product_images")

    def get_context_data(self, **kwargs):
        context = super(ProductDetailView, self).get_context_data(**kwargs)
        context["images"] = self.get_object().product_images.all() # type: ignore
        return context