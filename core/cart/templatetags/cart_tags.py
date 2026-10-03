from django import template

from shop.models import ProductModel,ProductStatusType

register = template.Library()

@register.filter
def get_product_from_id(product_id):
    return ProductModel.objects.get(id=product_id)
