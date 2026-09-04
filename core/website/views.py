from django.views import generic
from django.db.models import Prefetch


from shop.models import ProductModel,ProductCategory,ProductStatusType

# Create your views here.


class IndexShowView(generic.ListView):

    template_name = "website/index.html"

    queryset = ProductModel.objects.published()[:3] #type: ignore

    context_object_name = "products"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        categories = ProductCategory.objects.prefetch_related(
            Prefetch(
                "products",
                queryset=ProductModel.objects.filter(
                    status=ProductStatusType.publish.value
                )[:3],
                to_attr="category_products"
            )
        )[:3]

        context["categories"] = categories

        return context


class ContactTemplateView(generic.TemplateView):
    template_name = "website/contact.html"


class AboutTemplateView(generic.TemplateView):
    template_name = "website/about.html"
