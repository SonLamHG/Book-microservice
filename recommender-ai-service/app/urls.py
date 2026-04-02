from django.urls import path
from .views import AdvisorRecommendations, Recommendations, health_check

urlpatterns = [
    path('recommendations/<int:customer_id>/', Recommendations.as_view()),
    path('advisor/recommendations/', AdvisorRecommendations.as_view()),
    path('health/', health_check),
]
