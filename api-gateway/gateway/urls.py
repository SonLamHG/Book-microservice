from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # Books
    path('books/', views.book_list, name='book_list'),
    path('books/create/', views.book_create, name='book_create'),
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/register/', views.customer_register, name='customer_register'),
    # Cart
    path('cart/<int:customer_id>/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    # Orders
    path('orders/<int:customer_id>/', views.order_list, name='order_list'),
    path('orders/create/', views.create_order, name='create_order'),
    # Reviews
    path('reviews/book/<int:book_id>/', views.book_reviews, name='book_reviews'),
    path('reviews/add/', views.add_review, name='add_review'),
    # Recommendations
    path('recommendations/<int:customer_id>/', views.recommendations, name='recommendations'),
    # Staff
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    # Managers
    path('managers/', views.manager_list, name='manager_list'),
    path('managers/create/', views.manager_create, name='manager_create'),
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
]
