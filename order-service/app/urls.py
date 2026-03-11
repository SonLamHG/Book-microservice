from django.urls import path
from .views import OrderListCreate, OrderDetail, health_check

urlpatterns = [
    path('orders/', OrderListCreate.as_view()),
    path('orders/<int:pk>/', OrderDetail.as_view()),
    path('health/', health_check),
]
