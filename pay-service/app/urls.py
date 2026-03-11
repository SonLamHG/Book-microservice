from django.urls import path
from .views import PaymentListCreate, PaymentDetail, CancelPayment, health_check

urlpatterns = [
    path('payments/', PaymentListCreate.as_view()),
    path('payments/<int:pk>/', PaymentDetail.as_view()),
    path('payments/<int:pk>/cancel/', CancelPayment.as_view()),
    path('health/', health_check),
]
