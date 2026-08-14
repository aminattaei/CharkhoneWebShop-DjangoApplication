from django.db.models import Q
from django.views import generic

from .models import ProductCategory, ProductModel, ProductStatusType

ORDER_BY_CHOICES = {
    "-created_date",
    "created_date",
    "-price",
    "price",
}


class ProductListView(generic.ListView):
    model = ProductModel
    template_name = "shop/product-grid.html"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            ProductModel.objects.filter(status=ProductStatusType.publish)
            .select_related("category", "user")
            .order_by("-created_date")
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(brief_description__icontains=q)
                | Q(description__icontains=q)
            )

        min_price = self.request.GET.get("min_price", "").strip()
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.GET.get("max_price", "").strip()
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        category_id = self.request.GET.get("category_id", "").strip()
        if category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)

        order_by = self.request.GET.get("order_by", "")
        if order_by in ORDER_BY_CHOICES:
            queryset = queryset.order_by(order_by)

        return queryset

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