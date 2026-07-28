from django.views.generic import ListView

from .models import ProductModel, ProductStatusType


class ProductListView(ListView):
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
