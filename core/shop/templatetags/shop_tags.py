from django import template

register = template.Library()


@register.inclusion_tag("shop/_product_card.html", takes_context=True)
def render_products(context, products, columns="col-lg-3 col-md-4 col-sm-6"):
    return {
        "products": products,
        "columns": columns,
        "request": context.get("request"),
    }
