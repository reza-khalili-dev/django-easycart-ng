"""
URL configuration for testproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from cart.views import (
    add_to_cart,
    add_to_wishlist,
    cart_detail,
    clear_cart,
    remove_from_cart,
    remove_from_wishlist,
    update_cart_quantity,
    wishlist_detail,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cart/", cart_detail, name="cart_detail"),
    path("cart/add/", add_to_cart, name="add_to_cart"),
    path("cart/remove/", remove_from_cart, name="remove_from_cart"),
    path("cart/update-quantity", update_cart_quantity, name="update_cart_quantity"),
    path("cart/clear", clear_cart, name="clear_cart"),
    path("cart/wishlist/", wishlist_detail, name="wishlist_detail"),
    path("cart/wishlist/add", add_to_wishlist, name="add_to_wishlist"),
    path("cart/wishlist/remove/", remove_from_wishlist, name="remove_from_wishlist"),
]
