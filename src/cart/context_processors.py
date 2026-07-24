"""
Context processors for django-easy-cart.

This module provides context processors to make cart data available
to all templates across the entire project.
"""

from .models import Cart


def cart_total(request):
    """
    Make cart information available to all templates.

    Adds the following variables to the template context:
    - cart: The user's cart object (or None)
    - cart_total_price: The total price of all items in the cart
    - cart_total_items: The total number of items in the cart
    """
    cart = None
    total_price = 0
    total_items = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            total_price = cart.get_total_price()
            total_items = cart.get_total_items()
        except Cart.DoesNotExist:
            pass

    return {
        "cart": cart,
        "cart_total_price": total_price,
        "cart_total_items": total_items,
    }
