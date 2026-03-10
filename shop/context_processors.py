from .models import Category,SiteSettings


def cart_item_count(request):
    cart = request.session.get('cart', {})
    total_quantity = sum(int(item['quantity']) for item in cart.values())
    return {'cart_item_count': total_quantity}


def categories_context(request):
    return {
        'categories': Category.objects.all()
    }


def site_settings(request):
    settings = SiteSettings.objects.first()
    return {"settings": settings}

