from django.urls import path
from .views import PaymentListCreate, PaymentDetail

urlpatterns = [
    path('payments/', PaymentListCreate.as_view()),
    path('payments/<int:pk>/', PaymentDetail.as_view()),
]
