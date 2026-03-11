from django.urls import path
from .views import Register, Login, VerifyToken, UserList, health_check

urlpatterns = [
    path('auth/register/', Register.as_view()),
    path('auth/login/', Login.as_view()),
    path('auth/verify/', VerifyToken.as_view()),
    path('auth/users/', UserList.as_view()),
    path('health/', health_check),
]
