from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # Books
    path('books/', views.book_list, name='book_list'),
    path('books/create/', views.book_create, name='book_create'),
    path('books/<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('books/<int:pk>/delete/', views.book_delete, name='book_delete'),
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/register/', views.customer_register, name='customer_register'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    # Cart
    path('cart/<int:customer_id>/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/item/<int:item_id>/remove/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/item/<int:item_id>/update/', views.update_cart_item, name='update_cart_item'),
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
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),
    # Managers
    path('managers/', views.manager_list, name='manager_list'),
    path('managers/create/', views.manager_create, name='manager_create'),
    path('managers/<int:pk>/edit/', views.manager_edit, name='manager_edit'),
    path('managers/<int:pk>/delete/', views.manager_delete, name='manager_delete'),
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    # Advisory Chat
    path('chat/api/', views.advisory_chat_api, name='advisory_chat_api'),
    path('behavior/<int:customer_id>/', views.advisory_behavior, name='advisory_behavior'),
    # Auth
    path('auth/login/', views.auth_login, name='auth_login'),
    path('auth/register/', views.auth_register, name='auth_register'),
    path('auth/logout/', views.auth_logout, name='auth_logout'),
    # Health
    path('health/', views.health_check, name='health_check'),
]
