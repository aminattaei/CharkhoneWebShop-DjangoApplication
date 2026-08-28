from django import template
from shop.models import ProductModel

register = template.Library()


@register.inclusion_tag("shop/components/best_sellers.html")
def best_sellers():
    products = ProductModel.objects.published()
    return {
        "products": products,
    }