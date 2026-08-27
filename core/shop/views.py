from django.views import generic

from .models import ProductModel, ProductStatusType


class ProductListView(generic.ListView):
    model = ProductModel
    template_name = "shop/product-grid.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        return (
            ProductModel.objects.filter(status=ProductStatusType.publish)
            .select_related("category", "user")
            .order_by("-created_date")
        )


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
