from django.urls import path
from .views import OrderListCreate, OrderDetail

urlpatterns = [
    path('orders/', OrderListCreate.as_view()),
    path('orders/<int:pk>/', OrderDetail.as_view()),
]
