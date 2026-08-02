"""
Models for django-easy-cart.

This module defines the core data models for the shopping cart system:
- Cart: Represents a user's shopping cart
- CartItem: Represents individual items within a cart
- Wishlist: Represents a user's wishlist of products
"""

from decimal import Decimal
from typing import Any, Optional, Union

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    """
    A shopping cart belonging to a single user.

    Each user can have only one cart. The cart stores items through
    related CartItem objects and provides methods to calculate totals.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name=_("user"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("cart")
        verbose_name_plural = _("carts")
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Cart #{self.id} - {self.user}"

    def get_total_price(self) -> Decimal:
        """Calculate the total price of all items in the cart."""
        return sum(item.get_total_price() for item in self.items.all())

    def get_total_items(self) -> int:
        """Calculate the total quantity of all items in the cart."""
        return sum(item.quantity for item in self.items.all())

    def clear(self) -> None:
        """Remove all items from the cart."""
        self.items.all().delete()

    def add_item(
        self,
        product_id: Union[int, str],
        quantity: int = 1,
        price: Optional[Decimal] = None,
        **extra_data: Any,
    ) -> "CartItem":
        """
        Add an item to the cart or update quantity if it already exists.
        """
        existing_item = self.items.filter(
            product_id=product_id,
            extra_data=extra_data,
        ).first()

        if existing_item:
            existing_item.quantity += quantity
            if price is not None:
                existing_item.price = price
            existing_item.save()
            return existing_item
        else:
            return CartItem.objects.create(
                cart=self,
                product_id=product_id,
                quantity=quantity,
                price=price or Decimal("0.00"),
                extra_data=extra_data,
            )

    def remove_item(self, item_id: int) -> None:
        """Remove a specific item from the cart."""
        self.items.filter(id=item_id).delete()

    def update_quantity(self, item_id: int, quantity: int) -> "CartItem":
        """
        Update the quantity of a specific cart item.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")

        item = self.items.get(id=item_id)
        item.quantity = quantity
        item.save()
        return item


class CartItem(models.Model):
    """
    An individual item within a cart.

    Stores product reference and quantity. The product_id is intentionally
    generic to work with any product model in the host project.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("cart"),
    )
    product_id = models.CharField(
        max_length=255,
        verbose_name=_("product ID"),
        help_text=_("ID of the product (can be integer or string)"),
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("quantity"),
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("price"),
        help_text=_("Price per unit at the time of adding to cart"),
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("extra data"),
        help_text=_("Additional data to store with this item"),
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("added at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("cart item")
        verbose_name_plural = _("cart items")
        ordering = ["-added_at"]
        unique_together = ["cart", "product_id", "extra_data"]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product_id} (cart #{self.cart.id})"

    def get_total_price(self) -> Decimal:
        """Calculate the total price for this cart item."""
        return self.quantity * self.price


class Wishlist(models.Model):
    """
    A wishlist belonging to a single user.

    Users can add products to their wishlist for future purchase.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
        verbose_name=_("user"),
    )
    product_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("product IDs"),
        help_text=_("List of product IDs in the wishlist"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("wishlist")
        verbose_name_plural = _("wishlists")
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Wishlist #{self.id} - {self.user}"

    def add_product(self, product_id: Union[int, str]) -> None:
        """Add a product to the wishlist."""
        if product_id not in self.product_ids:
            self.product_ids.append(product_id)
            self.save()

    def remove_product(self, product_id: Union[int, str]) -> None:
        """Remove a product from the wishlist."""
        if product_id in self.product_ids:
            self.product_ids.remove(product_id)
            self.save()

    def has_product(self, product_id: Union[int, str]) -> bool:
        """Check if a product is in the wishlist."""
        return product_id in self.product_ids

    def get_product_count(self) -> int:
        """Get the number of products in the wishlist."""
        return len(self.product_ids)
