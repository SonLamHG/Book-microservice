from django.urls import path
from .views import Recommendations, health_check

urlpatterns = [
    path('recommendations/<int:customer_id>/', Recommendations.as_view()),
    path('health/', health_check),
]
