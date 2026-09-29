import logging

from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .cart import CartSession
from shop.models import ProductModel

logger = logging.getLogger(__name__)


class AddToCartView(View):
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
