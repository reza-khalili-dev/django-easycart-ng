"""
Tests for the cart models.

This module contains test cases for the Cart, CartItem, and Wishlist models
to ensure they function correctly.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from cart.models import Cart, CartItem, Wishlist

User = get_user_model()


class CartModelTest(TestCase):
    """Test cases for the Cart model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_creation(self):
        """Test that a cart is created with correct attributes."""
        self.assertEqual(self.cart.user.username, "testuser")
        self.assertIsNotNone(self.cart.created_at)
        self.assertIsNotNone(self.cart.updated_at)

    def test_cart_str_method(self):
        """Test the string representation of a cart."""
        expected = f"Cart #{self.cart.id} - {self.user}"
        self.assertEqual(str(self.cart), expected)

    def test_add_item_to_cart(self):
        """Test adding an item to the cart."""
        cart_item = self.cart.add_item(
            product_id="test-product-1",
            quantity=2,
            price=Decimal("19.99"),
            size="Large",
        )

        self.assertEqual(cart_item.product_id, "test-product-1")
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.price, Decimal("19.99"))
        self.assertEqual(cart_item.extra_data, {"size": "Large"})
        self.assertEqual(self.cart.get_total_items(), 2)
        self.assertEqual(self.cart.get_total_price(), Decimal("39.98"))

    def test_add_existing_item_updates_quantity(self):
        """Test that adding an existing item increases its quantity."""
        self.cart.add_item(
            product_id="test-product-1",
            quantity=1,
            price=Decimal("10.00"),
        )
        self.cart.add_item(
            product_id="test-product-1",
            quantity=3,
            price=Decimal("10.00"),
        )

        items = self.cart.items.filter(product_id="test-product-1")
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity, 4)
        self.assertEqual(self.cart.get_total_items(), 4)
        self.assertEqual(self.cart.get_total_price(), Decimal("40.00"))

    def test_remove_item_from_cart(self):
        """Test removing an item from the cart."""
        cart_item = self.cart.add_item(
            product_id="test-product-1",
            quantity=2,
            price=Decimal("19.99"),
        )
        self.assertEqual(self.cart.get_total_items(), 2)

        self.cart.remove_item(cart_item.id)
        self.assertEqual(self.cart.get_total_items(), 0)
        self.assertEqual(self.cart.get_total_price(), Decimal("0.00"))

    def test_clear_cart(self):
        """Test clearing all items from the cart."""
        self.cart.add_item(product_id="item-1", quantity=1, price=Decimal("5.00"))
        self.cart.add_item(product_id="item-2", quantity=3, price=Decimal("2.50"))

        self.assertEqual(self.cart.get_total_items(), 4)
        self.cart.clear()
        self.assertEqual(self.cart.get_total_items(), 0)
        self.assertEqual(self.cart.get_total_price(), Decimal("0.00"))

    def test_update_quantity(self):
        """Test updating the quantity of an item."""
        cart_item = self.cart.add_item(
            product_id="test-product-1",
            quantity=2,
            price=Decimal("10.00"),
        )

        updated_item = self.cart.update_quantity(cart_item.id, 5)
        self.assertEqual(updated_item.quantity, 5)
        self.assertEqual(self.cart.get_total_items(), 5)
        self.assertEqual(self.cart.get_total_price(), Decimal("50.00"))

    def test_update_quantity_raises_error_for_zero(self):
        """Test that updating quantity to 0 raises ValueError."""
        cart_item = self.cart.add_item(
            product_id="test-product-1",
            quantity=2,
            price=Decimal("10.00"),
        )

        with self.assertRaises(ValueError) as context:
            self.cart.update_quantity(cart_item.id, 0)
        self.assertEqual(str(context.exception), "Quantity must be greater than 0")


class CartItemModelTest(TestCase):
    """Test cases for the CartItem model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product_id="test-item",
            quantity=3,
            price=Decimal("7.50"),
            extra_data={"color": "blue"},
        )

    def test_cart_item_creation(self):
        """Test that a cart item is created with correct attributes."""
        self.assertEqual(self.cart_item.product_id, "test-item")
        self.assertEqual(self.cart_item.quantity, 3)
        self.assertEqual(self.cart_item.price, Decimal("7.50"))
        self.assertEqual(self.cart_item.extra_data, {"color": "blue"})

    def test_cart_item_str_method(self):
        """Test the string representation of a cart item."""
        expected = f"3 x test-item (cart #{self.cart.id})"
        self.assertEqual(str(self.cart_item), expected)

    def test_get_total_price(self):
        """Test calculating the total price of a cart item."""
        self.assertEqual(self.cart_item.get_total_price(), Decimal("22.50"))


class WishlistModelTest(TestCase):
    """Test cases for the Wishlist model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.wishlist = Wishlist.objects.create(user=self.user)

    def test_wishlist_creation(self):
        """Test that a wishlist is created with correct attributes."""
        self.assertEqual(self.wishlist.user.username, "testuser")
        self.assertIsNotNone(self.wishlist.created_at)
        self.assertEqual(self.wishlist.product_ids, [])

    def test_wishlist_str_method(self):
        """Test the string representation of a wishlist."""
        expected = f"Wishlist #{self.wishlist.id} - {self.user}"
        self.assertEqual(str(self.wishlist), expected)

    def test_add_product_to_wishlist(self):
        """Test adding a product to the wishlist."""
        self.wishlist.add_product("product-1")
        self.wishlist.add_product("product-2")

        self.assertEqual(self.wishlist.product_ids, ["product-1", "product-2"])
        self.assertEqual(self.wishlist.get_product_count(), 2)

    def test_remove_product_from_wishlist(self):
        """Test removing a product from the wishlist."""
        self.wishlist.add_product("product-1")
        self.wishlist.add_product("product-2")
        self.wishlist.remove_product("product-1")

        self.assertEqual(self.wishlist.product_ids, ["product-2"])
        self.assertEqual(self.wishlist.get_product_count(), 1)

    def test_has_product(self):
        """Test checking if a product is in the wishlist."""
        self.wishlist.add_product("product-1")
        self.assertTrue(self.wishlist.has_product("product-1"))
        self.assertFalse(self.wishlist.has_product("product-2"))

    def test_add_duplicate_product(self):
        """Test that adding a duplicate product does not create duplicates."""
        self.wishlist.add_product("product-1")
        self.wishlist.add_product("product-1")

        self.assertEqual(self.wishlist.product_ids, ["product-1"])
        self.assertEqual(self.wishlist.get_product_count(), 1)