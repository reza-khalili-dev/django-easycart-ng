"""
Admin configuration for django-easy-cart.

This module registers the Cart, CartItem, and Wishlist models
with the Django admin interface for easy management.
"""

from django.contrib import admin

from .models import Cart, CartItem, Wishlist


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin configuration for Cart model."""

    list_display = ("id", "user", "get_total_price", "get_total_items", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at", "get_total_price", "get_total_items")
    ordering = ("-updated_at",)

    def get_total_price(self, obj: Cart) -> str:
        """Display total price in admin."""
        return f"${obj.get_total_price():.2f}"
    get_total_price.short_description = "Total Price"

    def get_total_items(self, obj: Cart) -> int:
        """Display total items count in admin."""
        return obj.get_total_items()
    get_total_items.short_description = "Total Items"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin configuration for CartItem model."""

    list_display = ("id", "cart", "product_id", "quantity", "price", "get_total_price", "added_at")
    list_filter = ("added_at", "cart")
    search_fields = ("product_id", "cart__user__username", "cart__user__email")
    readonly_fields = ("added_at", "updated_at", "get_total_price")
    ordering = ("-added_at",)

    def get_total_price(self, obj: CartItem) -> str:
        """Display total price for this item in admin."""
        return f"${obj.get_total_price():.2f}"
    get_total_price.short_description = "Total Price"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Admin configuration for Wishlist model."""

    list_display = ("id", "user", "get_product_count", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at", "get_product_count")
    ordering = ("-updated_at",)

    def get_product_count(self, obj: Wishlist) -> int:
        """Display number of products in wishlist."""
        return obj.get_product_count()
    get_product_count.short_description = "Product Count"