from django.urls import path
from .views import ManagerListCreate, ManagerDetail, health_check

urlpatterns = [
    path('managers/', ManagerListCreate.as_view()),
    path('managers/<int:pk>/', ManagerDetail.as_view()),
    path('health/', health_check),
]
