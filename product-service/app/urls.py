from django.urls import path
from . import views

urlpatterns = [
    path("healthz", views.health_check, name="healthz"),
    path("api/v1/products/", views.ProductListCreate.as_view(), name="product-list"),
    path("api/v1/products/<int:pk>/", views.ProductDetail.as_view(), name="product-detail"),
    path("api/v1/categories/", views.CategoryListCreate.as_view(), name="category-list"),
    path("api/v1/categories/<int:pk>/", views.CategoryDetail.as_view(), name="category-detail"),
]