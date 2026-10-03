from django.http import JsonResponse
from django.views import View
from django.views import generic
from django.http import JsonResponse
from django.views.decorators.http import require_POST


import logging
import json

from .cart import CartSession


from .cart import CartSession
from shop.models import ProductModel

logger = logging.getLogger(__name__)


class CartAddToCartView(View):
    def post(self, request):
        product_id = request.POST.get("product_id")
        logger.info(f"AddToCartView POST: product_id={product_id}, session_key={request.session.session_key}, user={request.user}")
        
        if not product_id:
            logger.warning("No product_id in POST")
            return JsonResponse(
                {"detail": "شناسه محصول نامعتبر است."},
                status=400,
            )

        try:
            product = ProductModel.objects.get(pk=product_id)
        except ProductModel.DoesNotExist:
            logger.warning(f"Product not found: {product_id}")
            return JsonResponse(
                {"detail": "محصول پیدا نشد."},
                status=404,
            )

        cart = CartSession(request.session)
        logger.info(f"Cart before add: items={cart.items}")
        cart.add_product(product_id)
        cart.save()
        
        logger.info(f"Cart after add: items={cart.items}, total_items={cart.total_items}")
        logger.info(f"Session modified: {request.session.modified}")

        return JsonResponse({
            "detail": "محصول به سبد خرید اضافه شد.",
            "total_items": cart.total_items,
            "total_price": cart.total_price,
            "product_title": product.title,
        })


class CartSummaryTemplateView(generic.TemplateView):
    template_name = "cart/cart_summary.html"


class CartCheckoutTemplateView(generic.TemplateView):
    template_name = "cart/checkout.html"

@require_POST
def update_quantity(request):
    try:
        data = json.loads(request.body)

        try:
            product_id = int(data["product_id"])
            quantity = int(data["quantity"])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({
                "success": False,
                "message": "اطلاعات ارسال‌شده نامعتبر است."
            }, status=400)

        if quantity < 1:
            return JsonResponse({
                "success": False,
                "message": "تعداد محصول نامعتبر است."
            }, status=400)

        try:
            product = ProductModel.objects.get(pk=product_id)
        except ProductModel.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "محصول پیدا نشد."
            }, status=404)

        cart = CartSession(request.session)
        try:
            cart.update_quantity(product_id, quantity)
        except KeyError:
            return JsonResponse({
                "success": False,
                "message": "محصول در سبد خرید وجود ندارد."
            }, status=404)
        cart.save()

        return JsonResponse({
            "success": True,
            "total_items": cart.total_items,
            "total_price": cart.total_price,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "message": "اطلاعات ارسال‌شده نامعتبر است."
        }, status=400)