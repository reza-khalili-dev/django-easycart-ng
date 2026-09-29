"""
Tests for cart template tags:
get_cart_total_items,
get_cart_total_price,
get_cart_item_count,
multiply, currency_format
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from cart.models import Cart
from cart.templatetags.cart_tags import (
    currency_format,
    get_cart_item_count,
    get_cart_total_items,
    get_cart_total_price,
    multiply,
)

User = get_user_model()


class CartTagsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )
        self.factory = RequestFactory()

    def _context(self, user=None):
        request = self.factory.get("/")
        request.user = user if user is not None else AnonymousUser()
        return {"request": request}

    # get_cart_total_items
    def test_total_items_no_request_in_context(self):
        self.assertEqual(get_cart_total_items({}), 0)

    def test_total_items_anonymous_user(self):
        self.assertEqual(get_cart_total_items(self._context()), 0)

    def test_total_items_authenticated_no_cart(self):
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        self.assertEqual(get_cart_total_items(self._context(self.user)), 0)

    def test_total_items_authenticated_empty_cart(self):
        Cart.objects.create(user=self.user)
        self.assertEqual(get_cart_total_items(self._context(self.user)), 0)

    def test_total_items_authenticated_with_items(self):
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="product-1", quantity=2, price=Decimal("10.00"))
        cart.add_item(product_id="product-2", quantity=3, price=Decimal("5.00"))
        self.assertEqual(get_cart_total_items(self._context(self.user)), 5)

    # get_cart_total_price
    def test_total_price_no_request_in_context(self):
        self.assertEqual(get_cart_total_price({}), Decimal("0.00"))

    def test_total_price_anonymous_user(self):
        self.assertEqual(get_cart_total_price(self._context()), Decimal("0.00"))

    def test_total_price_authenticated_no_cart(self):
        self.assertEqual(
            get_cart_total_price(self._context(self.user)), Decimal("0.00")
        )

    def test_total_price_authenticated_with_items(self):
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="product-1", quantity=2, price=Decimal("10.00"))
        self.assertEqual(
            get_cart_total_price(self._context(self.user)), Decimal("20.00")
        )

    def test_total_price_authenticated_empty_cart_type_inconsistent(self):
        """
        BUG: same root cause documented on Cart.get_total_price() elsewhere.
        No cart / anonymous returns Decimal("0.00") explicitly, but an
        authenticated user with an existing EMPTY cart hits
        cart.get_total_price() -> sum() over empty queryset -> int 0.
        So this tag returns two different types for what looks like the
        same "empty cart" case depending on whether a Cart row exists yet.
        """
        Cart.objects.create(user=self.user)
        result = get_cart_total_price(self._context(self.user))
        self.assertEqual(result, 0)
        self.assertNotIsInstance(result, Decimal)  # documents the inconsistency

    # get_cart_item_count
    def test_item_count_no_product_id(self):
        self.assertEqual(get_cart_item_count(self._context(self.user)), 0)

    def test_item_count_no_request(self):
        self.assertEqual(get_cart_item_count({}, "product-1"), 0)

    def test_item_count_anonymous_user(self):
        self.assertEqual(get_cart_item_count(self._context(), "product-1"), 0)

    def test_item_count_authenticated_no_cart(self):
        self.assertEqual(get_cart_item_count(self._context(self.user), "product-1"), 0)

    def test_item_count_product_not_in_cart(self):
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="product-1", quantity=3, price=Decimal("10.00"))
        self.assertEqual(get_cart_item_count(self._context(self.user), "product-2"), 0)

    def test_item_count_product_in_cart(self):
        cart = Cart.objects.create(user=self.user)
        cart.add_item(product_id="product-1", quantity=3, price=Decimal("10.00"))
        self.assertEqual(get_cart_item_count(self._context(self.user), "product-1"), 3)

    def test_item_count_sums_across_multiple_rows_same_product(self):
        """
        Same product_id can exist as multiple CartItem rows if extra_data
        differs (e.g. different size/color variants). This documents
        expected behavior: the tag correctly sums quantity across all
        matching rows, not just the first one found.
        """
        cart = Cart.objects.create(user=self.user)
        cart.add_item(
            product_id="product-1", quantity=2, price=Decimal("10.00"), color="red"
        )
        cart.add_item(
            product_id="product-1", quantity=3, price=Decimal("10.00"), color="blue"
        )
        self.assertEqual(get_cart_item_count(self._context(self.user), "product-1"), 5)

    # multiply
    def test_multiply_two_ints(self):
        self.assertEqual(multiply(2, 3), 6)

    def test_multiply_float_and_int(self):
        self.assertEqual(multiply(2.5, 2), 5.0)

    def test_multiply_decimal_and_int(self):
        self.assertEqual(multiply(Decimal("2.50"), 2), Decimal("5.00"))

    def test_multiply_non_numeric_string_and_int_does_string_repetition(self):
        """
        BUG: same root cause as test_multiply_numeric_string_does_string_repetition.
        "abc" * 2 is valid Python (string repetition, not multiplication),
        so no exception is ever raised and the except (TypeError, ValueError)
        branch never triggers -- "abc" doesn't need to be numeric-looking
        to hit this, any string does.
        """
        result = multiply("abc", 2)
        self.assertEqual(result, "abcabc")
        self.assertNotEqual(result, 0)

    def test_multiply_none_returns_zero(self):
        self.assertEqual(multiply(None, 2), 0)

    def test_multiply_numeric_string_does_string_repetition(self):
        """
        BUG: multiply("3", 2) doesn't raise TypeError/ValueError -- Python
        allows str * int as string repetition. A numeric-looking string
        (e.g. coming from a form field or unconverted template context
        variable) silently produces "33" instead of the number 6, and
        the try/except never catches it because no exception is raised.

        PROPOSING FIX: explicitly reject/convert str values (or attempt
        Decimal/float coercion) before the multiplication, rather than
        relying on TypeError/ValueError to catch bad input.
        """
        result = multiply("3", 2)
        self.assertEqual(result, "33")
        self.assertNotEqual(result, 6)

    def test_multiply_int_and_numeric_string_does_string_repetition(self):
        """
        BUG: same root cause, reversed operand order -- 2 * "abc" is
        also valid Python (string repetition), so multiply(2, "abc")
        silently returns "abcabc" instead of erroring or computing
        numerically.
        """
        result = multiply(2, "abc")
        self.assertEqual(result, "abcabc")

    # currency_format
    def test_currency_format_int(self):
        self.assertEqual(currency_format(10), "$10.00")

    def test_currency_format_decimal(self):
        self.assertEqual(currency_format(Decimal("19.99")), "$19.99")

    def test_currency_format_numeric_string(self):
        self.assertEqual(currency_format("10.5"), "$10.50")

    def test_currency_format_non_numeric_string_returns_zero(self):
        self.assertEqual(currency_format("abc"), "$0.00")

    def test_currency_format_none_returns_zero(self):
        """
        @stringfilter forces value to str before the function body runs,
        so None becomes the string "None", and float("None") raises
        ValueError -- caught, falls back to "$0.00".
        """
        self.assertEqual(currency_format(None), "$0.00")

    def test_currency_format_negative_number_formatting(self):
        """
        BUG (minor/cosmetic): a negative price formats as "$-5.00"
        rather than the conventional "-$5.00". Not incorrect
        mathematically, but not standard currency display convention.

        PROPOSING FIX: format sign separately, e.g.
        f"-${abs(value):.2f}" if value < 0 else f"${value:.2f}"
        """
        self.assertEqual(currency_format(-5), "$-5.00")
        self.assertNotEqual(currency_format(-5), "-$5.00")

    def test_currency_format_zero(self):
        self.assertEqual(currency_format(0), "$0.00")
