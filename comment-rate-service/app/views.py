from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Avg
from .models import Review
from .serializers import ReviewSerializer


class ReviewListCreate(APIView):
    def get(self, request):
        reviews = Review.objects.all()
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookReviews(APIView):
    def get(self, request, book_id):
        reviews = Review.objects.filter(book_id=book_id)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        serializer = ReviewSerializer(reviews, many=True)
        return Response({
            "book_id": book_id,
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "total_reviews": reviews.count(),
            "reviews": serializer.data,
        })


class TopRatedBooks(APIView):
    """Returns book_ids ordered by average rating (for recommender service)."""
    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        top_books = (
            Review.objects.values('book_id')
            .annotate(avg_rating=Avg('rating'))
            .order_by('-avg_rating')[:limit]
        )
        return Response(list(top_books))


def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({'status': 'healthy', 'service': 'comment-rate-service'})
