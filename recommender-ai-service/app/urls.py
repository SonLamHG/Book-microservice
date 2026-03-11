from django.urls import path
from .views import Recommendations

urlpatterns = [
    path('recommendations/<int:customer_id>/', Recommendations.as_view()),
]
