from .cart import CartSession
from .models import Cart

def cart_processor(request):
    if request.user.is_authenticated:
        cart = Cart.get_or_create_for_user(request.user)
    else:
        cart = CartSession(request.session)
    return {'cart': cart}

