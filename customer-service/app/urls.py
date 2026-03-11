from django.urls import path
from .views import CustomerListCreate, CustomerDetail, health_check

urlpatterns = [
    path('customers/', CustomerListCreate.as_view()),
    path('customers/<int:pk>/', CustomerDetail.as_view()),
    path('health/', health_check),
]
