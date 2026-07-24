"""
Views for django-easy-cart.

This module provides view functions and classes for cart management:
- Add items to cart
- Remove items from cart
- Update item quantities
- View cart contents
"""


from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Cart, CartItem, Wishlist


def get_or_create_cart(request):
    """
    Get the current user's cart or create one if it doesn't exist.
    For authenticated users, uses the OneToOneField.
    For anonymous users, uses session-based cart (future implementation).
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    # For anonymous users, we'll implement session-based cart later
    return None


@login_required
def cart_detail(request):
    """Display the current user's cart."""
    cart = get_or_create_cart(request)
    context = {
        "cart": cart,
        "total_price": cart.get_total_price() if cart else 0,
        "total_items": cart.get_total_items() if cart else 0,
    }
    return render(request, "cart/cart_detail.html", context)


@login_required
@require_POST
def add_to_cart(request):
    """Add an item to the cart."""
    product_id = request.POST.get("product_id")
    quantity = int(request.POST.get("quantity", 1))
    price = request.POST.get("price")

    if not product_id:
        return JsonResponse({"error": "Product ID is required"}, status=400)

    cart = get_or_create_cart(request)
    extra_data = {}

    # Collect any extra data from POST
    for key, value in request.POST.items():
        if key not in ["product_id", "quantity", "price"]:
            extra_data[key] = value

    cart_item = cart.add_item(
        product_id=product_id, quantity=quantity, price=price, **extra_data
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Item added to cart",
            "item_id": cart_item.id,
            "total_items": cart.get_total_items(),
            "total_price": str(cart.get_total_price()),
        }
    )


@login_required
@require_POST
def remove_from_cart(request):
    """Remove an item from the cart."""
    item_id = request.POST.get("item_id")

    if not item_id:
        return JsonResponse({"error": "Item ID is required"}, status=400)

    cart = get_or_create_cart(request)
    cart.remove_item(item_id)

    return JsonResponse(
        {
            "success": True,
            "message": "Item removed from cart",
            "total_items": cart.get_total_items(),
            "total_price": str(cart.get_total_price()),
        }
    )


@login_required
@require_POST
def update_cart_quantity(request):
    """Update the quantity of a cart item."""
    item_id = request.POST.get("item_id")
    quantity = int(request.POST.get("quantity", 1))

    if not item_id:
        return JsonResponse({"error": "Item ID is required"}, status=400)

    if quantity <= 0:
        return JsonResponse({"error": "Quantity must be greater than 0"}, status=400)

    cart = get_or_create_cart(request)

    try:
        cart.update_quantity(item_id, quantity)
        return JsonResponse(
            {
                "success": True,
                "message": "Quantity updated",
                "total_items": cart.get_total_items(),
                "total_price": str(cart.get_total_price()),
            }
        )
    except CartItem.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)


@login_required
def clear_cart(request):
    """Clear all items from the cart."""
    cart = get_or_create_cart(request)
    cart.clear()

    return JsonResponse(
        {
            "success": True,
            "message": "Cart cleared",
            "total_items": 0,
            "total_price": "0.00",
        }
    )


# Wishlist Views
@login_required
def wishlist_detail(request):
    """Display the current user's wishlist."""
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    context = {
        "wishlist": wishlist,
        "product_count": wishlist.get_product_count(),
    }
    return render(request, "cart/wishlist_detail.html", context)


@login_required
@require_POST
def add_to_wishlist(request):
    """Add a product to the wishlist."""
    product_id = request.POST.get("product_id")

    if not product_id:
        return JsonResponse({"error": "Product ID is required"}, status=400)

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist.add_product(product_id)

    return JsonResponse(
        {
            "success": True,
            "message": "Product added to wishlist",
            "product_count": wishlist.get_product_count(),
        }
    )


@login_required
@require_POST
def remove_from_wishlist(request):
    """Remove a product from the wishlist."""
    product_id = request.POST.get("product_id")

    if not product_id:
        return JsonResponse({"error": "Product ID is required"}, status=400)

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist.remove_product(product_id)

    return JsonResponse(
        {
            "success": True,
            "message": "Product removed from wishlist",
            "product_count": wishlist.get_product_count(),
        }
    )
