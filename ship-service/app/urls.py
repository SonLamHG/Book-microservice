from django.urls import path
from .views import ShipmentListCreate, ShipmentDetail, CancelShipment, health_check

urlpatterns = [
    path('shipments/', ShipmentListCreate.as_view()),
    path('shipments/<int:pk>/', ShipmentDetail.as_view()),
    path('shipments/<int:pk>/cancel/', CancelShipment.as_view()),
    path('health/', health_check),
]
