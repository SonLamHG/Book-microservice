from django.urls import path
from .views import CartCreate, ViewCart, AddCartItem, UpdateCartItem, ClearCart

urlpatterns = [
    path('carts/', CartCreate.as_view()),
    path('carts/<int:customer_id>/', ViewCart.as_view()),
    path('carts/<int:customer_id>/clear/', ClearCart.as_view()),
    path('cart-items/', AddCartItem.as_view()),
    path('cart-items/<int:pk>/', UpdateCartItem.as_view()),
]
