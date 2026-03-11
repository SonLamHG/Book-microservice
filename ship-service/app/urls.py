from django.urls import path
from .views import ShipmentListCreate, ShipmentDetail

urlpatterns = [
    path('shipments/', ShipmentListCreate.as_view()),
    path('shipments/<int:pk>/', ShipmentDetail.as_view()),
]
