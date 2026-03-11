from django.urls import path
from .views import CategoryListCreate, CategoryDetail, health_check

urlpatterns = [
    path('categories/', CategoryListCreate.as_view()),
    path('categories/<int:pk>/', CategoryDetail.as_view()),
    path('health/', health_check),
]
