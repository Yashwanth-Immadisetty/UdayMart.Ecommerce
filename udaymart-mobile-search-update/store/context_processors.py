from .models import Cart, Category


def cart_count(request):
    """Make cart item count and categories available in all templates."""
    count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = cart.total_items
        except Cart.DoesNotExist:
            count = 0
    return {
        'cart_count': count,
        'categories_all': Category.objects.all(),
    }
