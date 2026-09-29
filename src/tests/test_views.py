"""
Tests for the cart views.

This module contains test cases for:
get_or_create_cart
cart_detail
add_to_cart
remove_from_cart
update_cart_quantity
clear_cart
wishlist_detail
add_to_wishlist
remove_from_wishlist
"""

from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db.utils import IntegrityError
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from cart.models import Cart, CartItem, Wishlist
from cart.views import get_or_create_cart

User = get_user_model()


class GetOrCreateCartTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.factory = RequestFactory()

    def test_creates_cart_for_authenticated_user_with_no_cart(self):
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

        request = self.factory.get("/")
        request.user = self.user
        cart = get_or_create_cart(request)

        self.assertIsNotNone(cart)
        self.assertEqual(cart.user, self.user)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_returns_existing_cart_for_authenticated_user(self):
        """
        edge: making a cart for someone who already has it, max 1 cart should exist
        """
        existing_cart = Cart.objects.create(user=self.user)

        request = self.factory.get("/")
        request.user = self.user
        cart = get_or_create_cart(request)

        self.assertEqual(cart, existing_cart)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)

    def test_returns_none_for_anonymous_user(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        cart = get_or_create_cart(request)

        self.assertIsNone(cart)


class CartDetailTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_auth_user_no_cart_detail(self):
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        response = self.client.get(reverse("cart_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_price"], 0)
        self.assertEqual(response.context["total_items"], 0)
        self.assertIsNotNone(response.context["cart"])
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_auth_user_with_empty_cart_detail(self):
        existing_cart = Cart.objects.create(user=self.user)
        response = self.client.get(reverse("cart_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_price"], 0)
        self.assertEqual(response.context["total_items"], 0)
        self.assertIsNotNone(response.context["cart"])
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_auth_user_with_nonempty_cart_detail(self):
        existing_cart = Cart.objects.create(user=self.user)
        existing_cart.add_item(
            product_id="test-product", quantity=2, price=Decimal("10.00")
        )

        response = self.client.get(reverse("cart_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cart"], existing_cart)
        self.assertEqual(response.context["total_items"], 2)
        self.assertEqual(response.context["total_price"], Decimal("20.00"))
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("cart_detail"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        self.assertIn("next=", response.url)

    # issue
    def test_total_price_type_when_cart_empty(self):
        """
        BUG: sum() over an empty queryset returns int 0, not Decimal("0.00"),
        so total_price is "0" for an empty cart but "X.XX" once items exist.
        Inconsistent client-facing format.
        """
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.get_total_price(), 0)
        self.assertNotIsInstance(cart.get_total_price(), Decimal)

    def test_total_price_string_format_inconsistent_when_empty(self):
        """
        BUG: same root cause as test_total_price_type_when_cart_empty, but
        shown at the string/JSON level that clients actually see. An empty
        cart's total_price serializes to "0", not "0.00" — so str(total_price)
        is neither equal to the int 0 nor to the Decimal-formatted "0.00"
        clients get once the cart has items.
        """
        cart = Cart.objects.create(user=self.user)

        empty_total = cart.get_total_price()
        self.assertEqual(str(empty_total), "0")
        self.assertNotEqual(str(empty_total), "0.00")

        cart.add_item(product_id="test-product", quantity=1, price=Decimal("0.00"))
        zero_priced_total = cart.get_total_price()
        self.assertEqual(str(zero_priced_total), "0.00")
        self.assertNotEqual(str(zero_priced_total), "0")


class AddToCartTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_get_request_rejected(self):
        """
        require_POST should 405 a GET without running the view body
        """
        response = self.client.get(reverse("add_to_cart"))
        self.assertEqual(response.status_code, 405)

    def test_csrf_token_not_leaked_into_extra_data(self):
        """
        BUG: the extra_data collection loop only excludes
        ["product_id", "quantity", "price"] -- it doesn't exclude
        Django's csrfmiddlewaretoken. With CSRF enforcement on, a real
        browser form POST includes this field, and it gets swept into
        extra_data and persisted on the CartItem.

        This test documents the bug by asserting it IS currently present
        (so the suite passes today). Once fixed, this assertion should
        be flipped to assertNotIn.

        PROPOSING FIX: add "csrfmiddlewaretoken" to the excluded keys
        list in add_to_cart's extra_data loop.
        """
        from django.middleware.csrf import get_token

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="testuser", password="testpass123")

        factory = RequestFactory()
        request = factory.get("/")
        request.session = csrf_client.session
        csrf_token = get_token(request)
        csrf_client.cookies["csrftoken"] = csrf_token

        response = csrf_client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
                "price": "10.00",
                "csrfmiddlewaretoken": csrf_token,
            },
        )
        self.assertEqual(response.status_code, 200)

        item = CartItem.objects.get(id=response.json()["item_id"])
        self.assertIn(
            "csrfmiddlewaretoken", item.extra_data
        )  # BUG: should be assertNotIn

    # product_id - edge
    def test_product_id_exceeds_max_length(self):
        """
        BUG: view never validates product_id length before saving.
        Should be rejected with 400;
        currently succeeds (silently truncated on SQLLite)
        or crashing (in other DB like PGSQL)

        PROPOSING FIX:
        add validator in the view
        """
        long_id = "x" * 500  # max_length=255
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": long_id,
                "quantity": 1,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_no_product_id(self):
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "quantity": 1,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Product ID is required")

    def test_empty_product_id(self):
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "",
                "quantity": 1,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Product ID is required")

    # quantity - edge
    def test_quantity_negative(self):
        """
        BUG: PositiveIntegerField's CHECK constraint blocks this at the DB,
        but the view doesn't catch it, so it crashes instead of 400

        PROPOSING FIX:
        add validator in the view
        """
        with self.assertRaises(IntegrityError):
            self.client.post(
                reverse("add_to_cart"),
                {
                    "product_id": "test-product",
                    "quantity": -5,
                    "price": "10.00",
                },
            )

    def test_quantity_zero(self):
        """
        BUG: 0 passes PositiveIntegerField's >= 0 check, a CartItem row
        IS created with quantity=0 instead of being a no-op

        PROPOSING FIX:
        add validator in the view, reject quantity <= 0
        """
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 0,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["item_id"])  # a row was created despite qty=0
        self.assertEqual(data["total_items"], 0)
        self.assertEqual(
            Cart.objects.get(id=response.wsgi_request.user.cart.id).items.count(), 1
        )

    def test_quantity_zero_then_real_quantity_merges_into_same_row(self):
        """
        BUG: consequence of test_quantity_zero — add_item's existing-item
        lookup filters on (product_id, extra_data) only, not quantity, so
        the zero-row gets found and incremented by a later real add
        instead of the zero-row never existing in the first place

        PROPOSING FIX:
        same as test_quantity_zero — reject quantity <= 0 in the view
        """
        first = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 0,
                "price": "10.00",
            },
        )
        self.assertEqual(first.status_code, 200)
        first_item_id = first.json()["item_id"]

        second = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 5,
                "price": "10.00",
            },
        )
        self.assertEqual(second.status_code, 200)
        data = second.json()

        # Same row reused, not a new one
        self.assertEqual(data["item_id"], first_item_id)
        self.assertEqual(data["total_items"], 5)

        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.get(id=first_item_id).quantity, 5)

    def test_quantity_extremely_large(self):
        """
        BUG: no upper bound on quantity anywhere — not in the view, not
        on the model field, not at the DB level (1 billion is still
        under Postgres's ~2.1B int ceiling)

        PROPOSING FIX:
        add a sane max quantity check in the view
        """
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 10**9,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_items"], 10**9)

    def test_quantity_non_numeric_string(self):
        """
        BUG: quantity = int(request.POST.get("quantity", 1)) runs BEFORE
        the product_id check, so a non-numeric quantity crashes with an
        uncaught ValueError -> 500, even if product_id is also missing.

        PROPOSING FIX: wrap the int() cast in try/except, return 400.
        """
        with self.assertRaises(ValueError):
            self.client.post(
                reverse("add_to_cart"),
                {
                    "product_id": "test-product",
                    "quantity": "abc",
                    "price": "10.00",
                },
            )

    def test_quantity_float_string(self):
        """
        BUG: int("2.5") also raises ValueError -- floats look like valid
        form input but aren't accepted.
        """
        with self.assertRaises(ValueError):
            self.client.post(
                reverse("add_to_cart"),
                {
                    "product_id": "test-product",
                    "quantity": "2.5",
                    "price": "10.00",
                },
            )

    # price - edge
    def test_price_negative(self):
        """
        BUG: no sign check anywhere, silently succeeds with a negative price

        PROPOSING FIX:
        add validator in the view, reject price < 0
        """
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
                "price": "-10.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_price"], "-10.00")

    def test_price_zero(self):
        """
        Free item 0.00 price
        """
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
                "price": "0.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_price"], "0.00")

    def test_price_missing_defaults_to_zero(self):
        """
        No BUG -- documents current behavior. price = request.POST.get("price")
        returns None when the key is absent entirely (not "0.00"), and
        add_item's `price or Decimal("0.00")` catches that None and
        defaults it to zero.
        """
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_price"], "0.00")

        item = CartItem.objects.get(id=data["item_id"])
        self.assertEqual(item.price, Decimal("0.00"))

    def test_price_exceeds_max_digits(self):
        """
        BUG: SQLite stores an oversized price fine on write, it blows up
        later on Decimal read instead of failing cleanly at input time

        PROPOSING FIX:
        add validator in the view, check digit count before saving
        """
        with self.assertRaises(InvalidOperation):
            self.client.post(
                reverse("add_to_cart"),
                {
                    "product_id": "test-product",
                    "quantity": 1,
                    "price": "99999999999.99",
                },
            )

    def test_price_non_numeric_string(self):
        """
        BUG: price is never cast/validated in the view -- the raw string
        is stored as-is and only breaks later. Verify exact failure mode
        (may be ValueError, TypeError, or InvalidOperation depending on
        where the bad string first gets used arithmetically) and pin down
        the real exception before relying on this assertion.

        PROPOSING FIX: parse price with Decimal(...) in the view inside a
        try/except InvalidOperation, return 400 on failure.
        """
        with self.assertRaises(Exception):
            self.client.post(
                reverse("add_to_cart"),
                {
                    "product_id": "test-product",
                    "quantity": 1,
                    "price": "abc",
                },
            )

    # expected
    def test_extra_data_passed_to_cart_item_expected(self):
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
                "price": "10.00",
                "color": "red",
                "size": "M",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Item added to cart")
        self.assertEqual(data["total_items"], 1)
        self.assertEqual(data["total_price"], "10.00")

        item = CartItem.objects.get(id=data["item_id"])
        self.assertEqual(item.extra_data, {"color": "red", "size": "M"})

    def test_no_extra_data_passed_to_cart_item_expected(self):
        response = self.client.post(
            reverse("add_to_cart"),
            {
                "product_id": "test-product",
                "quantity": 1,
                "price": "10.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Item added to cart")
        self.assertEqual(data["total_items"], 1)
        self.assertEqual(data["total_price"], "10.00")

        item = CartItem.objects.get(id=data["item_id"])
        self.assertEqual(item.extra_data, {})


class RemoveFromCartTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(reverse("remove_from_cart"), {"item_id": 1})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_get_request_rejected(self):
        response = self.client.get(reverse("remove_from_cart"))
        self.assertEqual(response.status_code, 405)

    # item_id - edge
    def test_no_item_id(self):
        response = self.client.post(reverse("remove_from_cart"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Item ID is required")

    def test_empty_item_id(self):
        response = self.client.post(reverse("remove_from_cart"), {"item_id": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Item ID is required")

    def test_nonexistent_item_id(self):
        """
        item_id well-formed but no such CartItem exists.
        """
        cart = Cart.objects.create(user=self.user)
        response = self.client.post(reverse("remove_from_cart"), {"item_id": 99999})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Item removed from cart")
        self.assertEqual(data["total_items"], 0)
        self.assertEqual(data["total_price"], "0")

    def test_malformed_item_id_non_numeric(self):
        """
        BUG: cart.remove_item(item_id) -> self.items.filter(id=item_id).delete()
        Django tries to coerce item_id to int for the id lookup; a
        non-numeric string raises an uncaught ValueError -> 500 instead
        of a clean 400.

        PROPOSING FIX: validate item_id is numeric before calling
        remove_item, same fix pattern as add_to_cart/update_cart_quantity.
        """
        cart = Cart.objects.create(user=self.user)
        with self.assertRaises(ValueError):
            self.client.post(reverse("remove_from_cart"), {"item_id": "abc"})

    # expected
    def test_success_response_shape(self):
        cart = Cart.objects.create(user=self.user)
        item = cart.add_item(
            product_id="test-product", quantity=2, price=Decimal("10.00")
        )

        response = self.client.post(reverse("remove_from_cart"), {"item_id": item.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"success", "message", "total_items", "total_price"},
        )
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Item removed from cart")
        self.assertEqual(data["total_items"], 0)
        self.assertEqual(data["total_price"], "0")

        self.assertFalse(CartItem.objects.filter(id=item.id).exists())


class UpdateCartQuantityTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": 1,
                "quantity": 2,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_get_request_rejected(self):
        response = self.client.get(reverse("update_cart_quantity"))
        self.assertEqual(response.status_code, 405)

    # item_id - edge
    def test_no_item_id(self):
        response = self.client.post(reverse("update_cart_quantity"), {"quantity": 2})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Item ID is required")

    def test_empty_item_id(self):
        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": "",
                "quantity": 2,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Item ID is required")

    def test_nonexistent_item_id(self):
        """
        item_id well-formed (numeric) but no such CartItem exists.
        View correctly catches CartItem.DoesNotExist -> 404.
        """
        cart = Cart.objects.create(user=self.user)
        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": 99999,
                "quantity": 2,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Item not found")

    def test_malformed_item_id_non_numeric(self):
        """
        BUG: item_id="abc" isn't a Django lookup error the view catches.
        cart.update_quantity -> self.items.get(id=item_id) raises
        ValueError on a non-numeric string, not CartItem.DoesNotExist,
        so it's uncaught -> 500 instead of a clean 400/404.

        PROPOSING FIX: validate item_id is numeric before calling
        update_quantity, same as int(item_id) guarded with try/except.
        """
        cart = Cart.objects.create(user=self.user)
        with self.assertRaises(ValueError):
            self.client.post(
                reverse("update_cart_quantity"),
                {
                    "item_id": "abc",
                    "quantity": 2,
                },
            )

    # quantity - edge
    def test_quantity_zero(self):
        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": 1,
                "quantity": 0,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Quantity must be greater than 0")

    def test_quantity_negative(self):
        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": 1,
                "quantity": -5,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Quantity must be greater than 0")

    def test_quantity_non_numeric_string(self):
        """
        BUG: quantity = int(request.POST.get("quantity", 1)) runs BEFORE
        the item_id check, so a non-numeric quantity raises an uncaught
        ValueError -> 500, regardless of whether item_id is valid.

        PROPOSING FIX: wrap the int() cast in try/except and return 400.
        """
        with self.assertRaises(ValueError):
            self.client.post(
                reverse("update_cart_quantity"),
                {
                    "item_id": 1,
                    "quantity": "abc",
                },
            )

    def test_quantity_float_string(self):
        """
        BUG: int("2.5") also raises ValueError -- floats aren't accepted
        even though they look like valid POST input from a form.
        """
        with self.assertRaises(ValueError):
            self.client.post(
                reverse("update_cart_quantity"),
                {
                    "item_id": 1,
                    "quantity": "2.5",
                },
            )

    def test_quantity_missing_defaults_to_one(self):
        """
        No BUG here -- documents current behavior: missing quantity
        silently defaults to 1 rather than erroring.
        """
        cart = Cart.objects.create(user=self.user)
        item = cart.add_item(
            product_id="test-product", quantity=5, price=Decimal("10.00")
        )

        response = self.client.post(
            reverse("update_cart_quantity"), {"item_id": item.id}
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_quantity_extremely_large(self):
        """
        BUG: no upper bound on quantity, same as add_to_cart.

        PROPOSING FIX: add a sane max quantity check, shared with add_to_cart.
        """
        cart = Cart.objects.create(user=self.user)
        item = cart.add_item(
            product_id="test-product", quantity=1, price=Decimal("10.00")
        )

        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": item.id,
                "quantity": 10**9,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_items"], 10**9)

    # expected
    def test_success_response_shape(self):
        cart = Cart.objects.create(user=self.user)
        item = cart.add_item(
            product_id="test-product", quantity=1, price=Decimal("10.00")
        )

        response = self.client.post(
            reverse("update_cart_quantity"),
            {
                "item_id": item.id,
                "quantity": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"success", "message", "total_items", "total_price"},
        )
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Quantity updated")
        self.assertEqual(data["total_items"], 3)
        self.assertEqual(data["total_price"], "30.00")

        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)


class ClearCartTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("clear_cart"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_post_request_allowed(self):
        """
        BUG: unlike add_to_cart/remove_from_cart/update_cart_quantity,
        clear_cart has no @require_POST decorator -- GET is allowed to
        mutate state. This violates the "GET must be safe" HTTP convention
        and means clearing a cart could be triggered by a prefetch, a
        crawler, or a link preview.

        PROPOSING FIX: add @require_POST to clear_cart, same as the
        other mutating views.
        """
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="test-product", quantity=2, price=Decimal("10.00"))

        response = self.client.get(reverse("clear_cart"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cart.items.count(), 0)  # GET alone cleared the cart

    # expected
    def test_success_response_shape(self):
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="test-product", quantity=2, price=Decimal("10.00"))

        response = self.client.get(reverse("clear_cart"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"success", "message", "total_items", "total_price"},
        )
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Cart cleared")
        self.assertEqual(data["total_items"], 0)
        self.assertEqual(data["total_price"], "0.00")

    def test_clears_all_items(self):
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="product-1", quantity=2, price=Decimal("10.00"))
        cart.add_item(product_id="product-2", quantity=1, price=Decimal("5.00"))
        self.assertEqual(cart.items.count(), 2)

        response = self.client.get(reverse("clear_cart"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cart.items.count(), 0)
        self.assertFalse(CartItem.objects.filter(cart=cart).exists())

    def test_clear_already_empty_cart(self):
        """
        Clearing a cart with no items is a safe no-op, not an error.
        """
        cart = Cart.objects.create(user=self.user)
        response = self.client.get(reverse("clear_cart"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_items"], 0)

    def test_clear_creates_cart_if_none_exists(self):
        """
        get_or_create_cart means clearing on a user with no cart yet
        doesn't error -- it creates an empty cart first, then clears it.
        """
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        response = self.client.get(reverse("clear_cart"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    # issue
    def test_total_price_response_hardcoded_not_computed(self):
        """
        Documents current behavior: total_price is a hardcoded "0.00"
        string literal in the view, not cart.get_total_price(). This
        happens to be correct after a real clear, but it's not actually
        reading the cart state -- if clear() ever partially failed, the
        response would still falsely report "0.00".
        """
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="test-product", quantity=1, price=Decimal("10.00"))

        response = self.client.get(reverse("clear_cart"))
        data = response.json()
        self.assertEqual(data["total_price"], "0.00")
        self.assertIsInstance(data["total_price"], str)


class WishListDetailTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("wishlist_detail"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        self.assertIn("next=", response.url)

    def test_get_request_allowed(self):
        """
        No require_POST on this view -- it's a read/display view, GET
        is the correct and only expected method. No POST-rejection test
        needed here, unlike the mutating views.
        """
        response = self.client.get(reverse("wishlist_detail"))
        self.assertEqual(response.status_code, 200)

    def test_deleted_user_with_stale_session(self):
        """
        edge: user is deleted mid-session (e.g. admin deletes the account)
        but the session cookie is still valid. AuthenticationMiddleware
        resolves request.user to AnonymousUser once the pk no longer
        exists, so login_required correctly redirects rather than
        crashing on a dangling FK.
        """
        self.user.delete()
        response = self.client.get(reverse("wishlist_detail"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    # expected
    def test_auth_user_no_wishlist_yet(self):
        """
        get_or_create means a wishlist is created on first visit if
        one doesn't already exist.
        """
        self.assertFalse(Wishlist.objects.filter(user=self.user).exists())
        response = self.client.get(reverse("wishlist_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["wishlist"])
        self.assertEqual(response.context["product_count"], 0)
        self.assertTrue(Wishlist.objects.filter(user=self.user).exists())

    def test_auth_user_with_empty_wishlist(self):
        existing_wishlist = Wishlist.objects.create(user=self.user)
        response = self.client.get(reverse("wishlist_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["wishlist"], existing_wishlist)
        self.assertEqual(response.context["product_count"], 0)

    def test_auth_user_with_nonempty_wishlist(self):
        existing_wishlist = Wishlist.objects.create(user=self.user)
        existing_wishlist.add_product("product-1")
        existing_wishlist.add_product("product-2")

        response = self.client.get(reverse("wishlist_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["wishlist"], existing_wishlist)
        self.assertEqual(response.context["product_count"], 2)

    def test_does_not_create_duplicate_wishlist(self):
        """
        edge: mirrors GetOrCreateCartTest.test_returns_existing_cart_for_authenticated_user
        -- max 1 wishlist per user, repeated visits shouldn't create more.
        """
        existing_wishlist = Wishlist.objects.create(user=self.user)
        self.client.get(reverse("wishlist_detail"))
        self.client.get(reverse("wishlist_detail"))

        self.assertEqual(Wishlist.objects.filter(user=self.user).count(), 1)

    # has_product / get_product_count, exercised via the wishlist the view creates
    def test_has_product_true_after_view_creates_wishlist(self):
        response = self.client.get(reverse("wishlist_detail"))
        wishlist = response.context["wishlist"]
        wishlist.add_product("product-1")

        self.assertTrue(wishlist.has_product("product-1"))

    def test_has_product_false_for_untracked_product(self):
        response = self.client.get(reverse("wishlist_detail"))
        wishlist = response.context["wishlist"]
        wishlist.add_product("product-1")

        self.assertFalse(wishlist.has_product("product-2"))

    def test_has_product_type_mismatch_int_vs_str(self):
        """
        BUG: product_ids is a raw JSONField list, "in" does exact type
        comparison. Adding the int 1 then checking has_product("1")
        (string) incorrectly returns False.

        PROPOSING FIX: normalize product_id to str on add/has/remove.
        """
        response = self.client.get(reverse("wishlist_detail"))
        wishlist = response.context["wishlist"]
        wishlist.add_product(1)

        self.assertTrue(wishlist.has_product(1))
        self.assertFalse(wishlist.has_product("1"))

    def test_get_product_count_matches_context_after_more_adds(self):
        response = self.client.get(reverse("wishlist_detail"))
        wishlist = response.context["wishlist"]
        wishlist.add_product("product-1")
        wishlist.add_product("product-2")
        wishlist.add_product("product-3")

        self.assertEqual(wishlist.get_product_count(), 3)

        # confirm the view's context reflects it on a fresh request too
        response = self.client.get(reverse("wishlist_detail"))
        self.assertEqual(response.context["product_count"], 3)

    def test_get_product_count_ignores_duplicate_adds(self):
        response = self.client.get(reverse("wishlist_detail"))
        wishlist = response.context["wishlist"]
        wishlist.add_product("product-1")
        wishlist.add_product("product-1")

        self.assertEqual(wishlist.get_product_count(), 1)


class AddToWishlistTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("add_to_wishlist"), {"product_id": "product-1"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_get_request_rejected(self):
        response = self.client.get(reverse("add_to_wishlist"))
        self.assertEqual(response.status_code, 405)

    # product_id - edge
    def test_no_product_id(self):
        response = self.client.post(reverse("add_to_wishlist"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Product ID is required")

    def test_empty_product_id(self):
        response = self.client.post(reverse("add_to_wishlist"), {"product_id": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Product ID is required")

    def test_product_id_extremely_long(self):
        """
        No BUG here (unlike cart's product_id, which is a CharField(255)
        with a real DB limit) -- Wishlist.product_ids is a JSONField list
        with no length constraint on individual entries, so an oversized
        string is accepted and stored as-is. Documents current behavior.
        """
        long_id = "x" * 10000
        response = self.client.post(reverse("add_to_wishlist"), {"product_id": long_id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        wishlist = Wishlist.objects.get(user=self.user)
        self.assertIn(long_id, wishlist.product_ids)

    def test_product_id_numeric_string_stored_as_string(self):
        """
        POST data always arrives as a string, even for a numeric-looking
        product_id like "123". Confirms it's stored as the string "123",
        not coerced to the int 123 -- relevant given has_product's
        int-vs-str mismatch bug documented elsewhere.
        """
        response = self.client.post(reverse("add_to_wishlist"), {"product_id": "123"})
        self.assertEqual(response.status_code, 200)

        wishlist = Wishlist.objects.get(user=self.user)
        self.assertIn("123", wishlist.product_ids)
        self.assertNotIn(123, wishlist.product_ids)

    def test_duplicate_product_id_not_added_twice(self):
        """
        add_product's own guard prevents duplicates -- product_count
        shouldn't increase on a repeat add of the same id.
        """
        self.client.post(reverse("add_to_wishlist"), {"product_id": "product-1"})
        response = self.client.post(
            reverse("add_to_wishlist"), {"product_id": "product-1"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product_count"], 1)

    # expected / message
    def test_success_response_shape(self):
        response = self.client.post(
            reverse("add_to_wishlist"), {"product_id": "product-1"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"success", "message", "product_count"},
        )
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Product added to wishlist")
        self.assertEqual(data["product_count"], 1)

    def test_error_message_matches_exactly(self):
        response = self.client.post(reverse("add_to_wishlist"), {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(set(data.keys()), {"error"})
        self.assertEqual(data["error"], "Product ID is required")

    def test_product_count_increments_across_multiple_distinct_adds(self):
        r1 = self.client.post(reverse("add_to_wishlist"), {"product_id": "product-1"})
        self.assertEqual(r1.json()["product_count"], 1)

        r2 = self.client.post(reverse("add_to_wishlist"), {"product_id": "product-2"})
        self.assertEqual(r2.json()["product_count"], 2)

        r3 = self.client.post(reverse("add_to_wishlist"), {"product_id": "product-3"})
        self.assertEqual(r3.json()["product_count"], 3)

    def test_creates_wishlist_if_none_exists(self):
        self.assertFalse(Wishlist.objects.filter(user=self.user).exists())
        response = self.client.post(
            reverse("add_to_wishlist"), {"product_id": "product-1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Wishlist.objects.filter(user=self.user).exists())


class ModelStrMethodsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )

    def test_cart_str(self):
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(str(cart), f"Cart #{cart.id} - {self.user}")

    def test_cart_item_str(self):
        cart = Cart.objects.create(user=self.user)
        item = cart.add_item(
            product_id="test-product", quantity=3, price=Decimal("10.00")
        )
        self.assertEqual(str(item), f"3 x test-product (cart #{cart.id})")

    def test_wishlist_str(self):
        wishlist = Wishlist.objects.create(user=self.user)
        self.assertEqual(str(wishlist), f"Wishlist #{wishlist.id} - {self.user}")


class RemoveFromWishlistTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="testpass123")

    # auth
    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "product-1"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_get_request_rejected(self):
        response = self.client.get(reverse("remove_from_wishlist"))
        self.assertEqual(response.status_code, 405)

    # product_id - edge
    def test_no_product_id(self):
        response = self.client.post(reverse("remove_from_wishlist"), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Product ID is required")

    def test_empty_product_id(self):
        response = self.client.post(reverse("remove_from_wishlist"), {"product_id": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Product ID is required")

    def test_nonexistent_product_id_is_noop(self):
        """
        remove_product's own "if product_id in self.product_ids" guard
        means removing a product that was never added is a safe no-op,
        not an error -- same pattern as remove_from_cart's nonexistent
        item_id case.
        """
        wishlist = Wishlist.objects.create(user=self.user)
        wishlist.add_product("product-1")

        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "does-not-exist"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["product_count"], 1)  # unaffected

    def test_remove_from_empty_wishlist_is_noop(self):
        wishlist = Wishlist.objects.create(user=self.user)
        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "anything"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["product_count"], 0)

    def test_product_id_type_mismatch_int_vs_str_fails_to_remove(self):
        """
        BUG: same root cause as has_product's int-vs-str mismatch.
        POST data always arrives as a string, so if a product was ever
        added as the int 1 (e.g. via direct model use, not this view),
        remove_from_wishlist's string "1" will never match it via
        remove_product's "in" check -- the int entry is stuck forever
        through this endpoint.

        PROPOSING FIX: normalize product_id to str consistently across
        add_product/remove_product/has_product.
        """
        wishlist = Wishlist.objects.create(user=self.user)
        wishlist.add_product(1)  # stored as int
        self.assertEqual(wishlist.get_product_count(), 1)

        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "1"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["product_count"], 1)  # BUG: still there, not removed

    def test_creates_wishlist_if_none_exists(self):
        """
        get_or_create means removing from a nonexistent wishlist doesn't
        error -- it creates an empty one first, then no-ops the removal.
        """
        self.assertFalse(Wishlist.objects.filter(user=self.user).exists())
        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "product-1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Wishlist.objects.filter(user=self.user).exists())

    # expected / message
    def test_success_response_shape(self):
        wishlist = Wishlist.objects.create(user=self.user)
        wishlist.add_product("product-1")

        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "product-1"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {"success", "message", "product_count"},
        )
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Product removed from wishlist")
        self.assertEqual(data["product_count"], 0)

    def test_error_message_matches_exactly(self):
        response = self.client.post(reverse("remove_from_wishlist"), {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(set(data.keys()), {"error"})
        self.assertEqual(data["error"], "Product ID is required")

    def test_product_count_decrements_correctly(self):
        wishlist = Wishlist.objects.create(user=self.user)
        wishlist.add_product("product-1")
        wishlist.add_product("product-2")
        wishlist.add_product("product-3")

        response = self.client.post(
            reverse("remove_from_wishlist"), {"product_id": "product-2"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product_count"], 2)

        wishlist.refresh_from_db()
        self.assertNotIn("product-2", wishlist.product_ids)
        self.assertIn("product-1", wishlist.product_ids)
        self.assertIn("product-3", wishlist.product_ids)

    def test_remove_then_readd_same_product(self):
        """
        edge: remove followed by re-add should work cleanly, not be
        blocked by any stale state.
        """
        wishlist = Wishlist.objects.create(user=self.user)
        wishlist.add_product("product-1")

        self.client.post(reverse("remove_from_wishlist"), {"product_id": "product-1"})
        response = self.client.post(
            reverse("add_to_wishlist"), {"product_id": "product-1"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product_count"], 1)
