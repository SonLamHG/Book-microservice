from django.urls import path
from .views import BehaviorProfileView, BehaviorTrainView, BehaviorStatusView, health_check

urlpatterns = [
    path('behavior/profile/', BehaviorProfileView.as_view()),
    path('behavior/train/', BehaviorTrainView.as_view()),
    path('behavior/status/', BehaviorStatusView.as_view()),
    path('health/', health_check),
]
