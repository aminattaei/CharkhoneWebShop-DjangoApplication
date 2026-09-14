from django import template

from shop.models import ProductModel,ProductStatusType

register = template.Library()


@register.inclusion_tag("shop/_product_card.html", takes_context=True)
def render_products(context, products, columns="col-lg-3 col-md-4 col-sm-6"):
    return {
        "products": products,
        "columns": columns,
        "request": context.get("request"),
    }


@register.inclusion_tag("shop/_related_products.html")
def show_related_products(product):
    related_products = ProductModel.objects.filter(status= ProductStatusType.publish.value ,category = product.category)[:4]
    return {"related_products":related_products}