from django.urls import path
from .views import StaffListCreate, StaffDetail, health_check

urlpatterns = [
    path('staff/', StaffListCreate.as_view()),
    path('staff/<int:pk>/', StaffDetail.as_view()),
    path('health/', health_check),
]
