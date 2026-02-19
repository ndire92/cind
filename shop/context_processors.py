from .models import Category


def cart_item_count(request):
    cart = request.session.get('cart', {})
    total_quantity = sum(int(item['quantity']) for item in cart.values())
    return {'cart_item_count': total_quantity}

from .models import Category

def categories_context(request):
    return {
        'categories': Category.objects.all()
    }