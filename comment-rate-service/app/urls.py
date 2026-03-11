from django.urls import path
from .views import ReviewListCreate, BookReviews, TopRatedBooks

urlpatterns = [
    path('reviews/', ReviewListCreate.as_view()),
    path('reviews/book/<int:book_id>/', BookReviews.as_view()),
    path('reviews/top-rated/', TopRatedBooks.as_view()),
]
