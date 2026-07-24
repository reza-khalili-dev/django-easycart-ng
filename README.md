# django-easycart-ng

[![PyPI version](https://badge.fury.io/py/django-easycart-ng.svg)](https://badge.fury.io/py/django-easycart-ng)
[![Python Version](https://img.shields.io/pypi/pyversions/django-easycart-ng.svg)](https://pypi.org/project/django-easycart-ng/)
[![Django Version](https://img.shields.io/badge/Django-3.2%20%7C%204.0%20%7C%205.0-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub issues](https://img.shields.io/github/issues/reza-khalili-dev/django-easycart-ng)](https://github.com/reza-khalili-dev/django-easycart-ng/issues)

**A simple and flexible shopping cart for Django projects.**

`django-easycart-ng` is a lightweight, reusable shopping cart app for Django. It provides essential cart functionality with a clean API, making it easy to integrate into any Django project.

---

## ✨ Features

- **Simple Cart Management**: Add, remove, and update items with ease.
- **Generic Product Support**: Works with any product model using a generic `product_id` field.
- **Wishlist**: Allow users to save products for later.
- **Session Support**: (Coming soon) Support for anonymous users via sessions.
- **Admin Integration**: Full admin interface for managing carts and wishlists.
- **Template Tags**: Easy access to cart data in templates.
- **Lightweight**: Minimal dependencies (only Django).
- **Extensible**: Easy to customize and extend.

---

## 📦 Installation

1. Install the package:

```bash
pip install django-easycart-ng
```

2. Add `cart` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "cart.apps.CartConfig",
    # ...
]
```

3. Run migrations:

```bash
python manage.py migrate
```

4. Add the context processor (optional but recommended):

```python
TEMPLATES = [
    {
        # ...
        "OPTIONS": {
            "context_processors": [
                # ...
                "cart.context_processors.cart_total",
            ],
        },
    },
]
```

---

## 🚀 Quick Start

Add an item to the cart:

```python
from cart.models import Cart

# Get or create the user's cart
cart, _ = Cart.objects.get_or_create(user=request.user)

# Add an item
cart.add_item(
    product_id=1,
    quantity=2,
    price=99.99,
    size="Large",  # Extra data
)
```

Get cart total:

```python
total_price = cart.get_total_price()
total_items = cart.get_total_items()
```

Use template tags:

```django
{% load cart_tags %}

<p>Total items: {% get_cart_total_items %}</p>
<p>Total price: ${% get_cart_total_price %}</p>

{% if request.user.is_authenticated %}
    <a href="{% url 'cart_detail' %}">View Cart</a>
{% endif %}
```

---

## 📚 API Reference

### Cart Model

| Method | Description |
|--------|-------------|
| `add_item(product_id, quantity=1, price=None, **extra_data)` | Add an item to the cart. |
| `remove_item(item_id)` | Remove an item from the cart. |
| `update_quantity(item_id, quantity)` | Update the quantity of an item. |
| `get_total_price()` | Return total price of all items. |
| `get_total_items()` | Return total number of items. |
| `clear()` | Remove all items from the cart. |

### Wishlist Model

| Method | Description |
|--------|-------------|
| `add_product(product_id)` | Add a product to the wishlist. |
| `remove_product(product_id)` | Remove a product from the wishlist. |
| `has_product(product_id)` | Check if a product is in the wishlist. |
| `get_product_count()` | Return the number of products in the wishlist. |

---

## 🛠️ Development Setup

To contribute to this package, follow these steps:

1. Clone the repository:

```bash
git clone https://github.com/reza-khalili-dev/django-easycart-ng.git
cd django-easycart-ng
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:

```bash
pip install -e .[dev]
```

4. Run tests:

```bash
pytest
```

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## ⭐ Show Your Support

If you find this package useful, please give it a ⭐ on [GitHub](https://github.com/reza-khalili-dev/django-easycart-ng)!

---

## 📧 Contact

- **Author:** Reza Khalili
- **Email:** arsalankhalili688@gmail.com
- **Linkedin** [www.linkedin.com/in/reza-khalili-developer](www.linkedin.com/in/reza-khalili-developer)
- **GitHub:** [https://github.com/reza-khalili-dev](https://github.com/reza-khalili-dev)