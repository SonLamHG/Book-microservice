from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

BOOK_SERVICE_URL = "http://book-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"


class Recommendations(APIView):
    """
    Simple recommendation engine:
    - Get top-rated books from comment-rate-service
    - Fetch book details from book-service
    - Return recommended books
    """
    def get(self, request, customer_id):
        limit = int(request.query_params.get('limit', 5))

        # Get top rated book IDs from comment-rate-service
        try:
            r = requests.get(
                f"{COMMENT_RATE_SERVICE_URL}/reviews/top-rated/",
                params={"limit": limit},
                timeout=5,
            )
            top_rated = r.json() if r.status_code == 200 else []
        except requests.exceptions.RequestException:
            top_rated = []

        recommended_books = []
        for item in top_rated:
            try:
                br = requests.get(
                    f"{BOOK_SERVICE_URL}/books/{item['book_id']}/",
                    timeout=5,
                )
                if br.status_code == 200:
                    book = br.json()
                    book['avg_rating'] = item.get('avg_rating')
                    recommended_books.append(book)
            except requests.exceptions.RequestException:
                continue

        # If not enough rated books, fill with latest books
        if len(recommended_books) < limit:
            try:
                br = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
                if br.status_code == 200:
                    all_books = br.json()
                    existing_ids = {b['id'] for b in recommended_books}
                    for book in all_books:
                        if book['id'] not in existing_ids:
                            recommended_books.append(book)
                        if len(recommended_books) >= limit:
                            break
            except requests.exceptions.RequestException:
                pass

        return Response({
            "customer_id": customer_id,
            "recommendations": recommended_books[:limit],
        })
