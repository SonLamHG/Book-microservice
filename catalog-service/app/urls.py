from django.urls import path
from .views import CategoryListCreate, CategoryDetail

urlpatterns = [
    path('categories/', CategoryListCreate.as_view()),
    path('categories/<int:pk>/', CategoryDetail.as_view()),
]
