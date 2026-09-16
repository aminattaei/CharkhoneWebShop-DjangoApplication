from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import generic, View
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import Http404
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction

from .filters import apply_product_filters

from .models import ProductCategory, ProductModel


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


