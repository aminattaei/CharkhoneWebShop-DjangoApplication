from .cart import CartSession

def cart_processor(request):
    Cart = CartSession(request.session)
    return {'cart':Cart}

