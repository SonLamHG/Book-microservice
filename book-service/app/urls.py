from django.urls import path
from .views import BookListCreate, BookDetail, health_check

urlpatterns = [
    path('books/', BookListCreate.as_view()),
    path('books/<int:pk>/', BookDetail.as_view()),
    path('health/', health_check),
]
