"""
Custom template tags for django-easy-cart.

This module provides template tags and filters for working with cart data
directly in Django templates.
"""

from decimal import Decimal

from django import template
from django.template.defaultfilters import stringfilter

from ..models import Cart

register = template.Library()


@register.simple_tag(takes_context=True)
def get_cart_total_items(context):
    """
    Get the total number of items in the user's cart.

    Usage:
        {% load cart_tags %}
        {% get_cart_total_items as total_items %}
        {{ total_items }}
    """
    request = context.get("request")
    if request and request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return cart.get_total_items()
        except Cart.DoesNotExist:
            pass
    return 0


@register.simple_tag(takes_context=True)
def get_cart_total_price(context):
    """
    Get the total price of the user's cart.

    Usage:
        {% load cart_tags %}
        {% get_cart_total_price as total_price %}
        {{ total_price }}
    """
    request = context.get("request")
    if request and request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return cart.get_total_price()
        except Cart.DoesNotExist:
            pass
    return Decimal("0.00")


@register.simple_tag(takes_context=True)
def get_cart_item_count(context, product_id=None):
    """
    Get the quantity of a specific product in the cart.

    Usage:
        {% load cart_tags %}
        {% get_cart_item_count product_id as count %}
        {{ count }}
    """
    request = context.get("request")
    if not product_id:
        return 0

    if request and request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            items = cart.items.filter(product_id=product_id)
            return sum(item.quantity for item in items)
        except Cart.DoesNotExist:
            pass
    return 0


@register.filter
def multiply(value, arg):
    """Multiply a value by an argument."""
    try:
        return value * arg
    except (TypeError, ValueError):
        return 0


@register.filter
@stringfilter
def currency_format(value):
    """
    Format a number as currency (USD by default).
    Usage: {{ price|currency_format }}
    """
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return f"${0:.2f}"
