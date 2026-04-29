from django.urls import path
from .views import (
    BookListCreate, BookDetail,
    ProductListCreate, ProductDetail,
    ElectronicsListCreate, ElectronicsDetail,
    FashionListCreate, FashionDetail,
    health_check,
)

urlpatterns = [
    # Legacy book contract — preserved for cart/order/review/recommender/advisory.
    path('books/', BookListCreate.as_view()),
    path('books/<int:pk>/', BookDetail.as_view()),

    # Generic product API — multi-type listings.
    path('products/', ProductListCreate.as_view()),
    path('products/<int:pk>/', ProductDetail.as_view()),

    # Type-specific APIs.
    path('electronics/', ElectronicsListCreate.as_view()),
    path('electronics/<int:pk>/', ElectronicsDetail.as_view()),
    path('fashion/', FashionListCreate.as_view()),
    path('fashion/<int:pk>/', FashionDetail.as_view()),

    path('health/', health_check),
]
