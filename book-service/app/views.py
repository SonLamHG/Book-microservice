from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Book
from .serializers import BookSerializer


class BookListCreate(APIView):
    def get(self, request):
        category_id = request.query_params.get('category_id')
        search = request.query_params.get('search', '').strip()

        if search:
            search_vector = SearchVector('title', 'author', 'description', 'isbn')
            search_query = SearchQuery(search, search_type='plain')
            books = Book.objects.annotate(
                rank=SearchRank(search_vector, search_query)
            ).filter(rank__gt=0).order_by('-rank')
            if category_id:
                books = books.filter(category_id=category_id)
            # Fallback to icontains if full-text search returns no results
            if not books.exists():
                books = Book.objects.filter(
                    models.Q(title__icontains=search) |
                    models.Q(author__icontains=search) |
                    models.Q(isbn__icontains=search)
                )
                if category_id:
                    books = books.filter(category_id=category_id)
        elif category_id:
            books = Book.objects.filter(category_id=category_id)
        else:
            books = Book.objects.all()

        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookDetail(APIView):
    def get(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookSerializer(book)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({'status': 'healthy', 'service': 'book-service'})
