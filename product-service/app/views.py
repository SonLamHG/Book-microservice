from django.db import models
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from .models import Product, Book, Electronics, Fashion
from .serializers import (
    ProductSerializer, BookSerializer, ElectronicsSerializer, FashionSerializer,
)


# ---------- /books/ — backward-compatible legacy contract ----------

class BookListCreate(APIView):
    def get(self, request):
        category_id = request.query_params.get('category_id')
        search = request.query_params.get('search', '').strip()

        qs = Book.objects.select_related('product').all()

        if search:
            search_vector = SearchVector('product__name', 'author', 'product__description', 'isbn')
            search_query = SearchQuery(search, search_type='plain')
            ranked = qs.annotate(rank=SearchRank(search_vector, search_query)) \
                       .filter(rank__gt=0).order_by('-rank')
            if category_id:
                ranked = ranked.filter(product__category_id=category_id)
            if not ranked.exists():
                ranked = qs.filter(
                    models.Q(product__name__icontains=search) |
                    models.Q(author__icontains=search) |
                    models.Q(isbn__icontains=search)
                )
                if category_id:
                    ranked = ranked.filter(product__category_id=category_id)
            qs = ranked
        elif category_id:
            qs = qs.filter(product__category_id=category_id)

        return Response(BookSerializer(qs, many=True).data)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookDetail(APIView):
    def get(self, request, pk):
        try:
            book = Book.objects.select_related('product').get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookSerializer(book).data)

    def put(self, request, pk):
        try:
            book = Book.objects.select_related('product').get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            book = Book.objects.select_related('product').get(pk=pk)
        except Book.DoesNotExist:
            return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        # Cascading via Product so the row in app_product is also removed.
        book.product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- /products/ — generic, multi-type ----------

class ProductListCreate(APIView):
    """List/create across all product types. Filter with ?type=book|electronics|fashion."""

    def get(self, request):
        ptype = request.query_params.get('type')
        category_id = request.query_params.get('category_id')
        search = request.query_params.get('search', '').strip()

        qs = Product.objects.all()
        if ptype:
            qs = qs.filter(product_type=ptype)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search)
            )
        return Response(ProductSerializer(qs, many=True).data)

    def post(self, request):
        # Generic creation requires the caller to also POST type-specific fields
        # via the dedicated endpoint. /products/ POST creates a bare Product row
        # — useful only for tests / admin scripts.
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetail(APIView):
    """Returns the type-specific representation when possible, falling back to the base Product."""

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_with_subtype(product))

    def put(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _serialize_with_subtype(product):
    if product.product_type == 'book' and hasattr(product, 'book_detail'):
        return BookSerializer(product.book_detail).data
    if product.product_type == 'electronics' and hasattr(product, 'electronics_detail'):
        return ElectronicsSerializer(product.electronics_detail).data
    if product.product_type == 'fashion' and hasattr(product, 'fashion_detail'):
        return FashionSerializer(product.fashion_detail).data
    return ProductSerializer(product).data


# ---------- /electronics/ ----------

class ElectronicsListCreate(APIView):
    def get(self, request):
        qs = Electronics.objects.select_related('product').all()
        category_id = request.query_params.get('category_id')
        if category_id:
            qs = qs.filter(product__category_id=category_id)
        return Response(ElectronicsSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ElectronicsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ElectronicsDetail(APIView):
    def get(self, request, pk):
        try:
            obj = Electronics.objects.select_related('product').get(pk=pk)
        except Electronics.DoesNotExist:
            return Response({"error": "Electronics not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ElectronicsSerializer(obj).data)

    def put(self, request, pk):
        try:
            obj = Electronics.objects.select_related('product').get(pk=pk)
        except Electronics.DoesNotExist:
            return Response({"error": "Electronics not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ElectronicsSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = Electronics.objects.select_related('product').get(pk=pk)
        except Electronics.DoesNotExist:
            return Response({"error": "Electronics not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- /fashion/ ----------

class FashionListCreate(APIView):
    def get(self, request):
        qs = Fashion.objects.select_related('product').all()
        category_id = request.query_params.get('category_id')
        if category_id:
            qs = qs.filter(product__category_id=category_id)
        return Response(FashionSerializer(qs, many=True).data)

    def post(self, request):
        serializer = FashionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FashionDetail(APIView):
    def get(self, request, pk):
        try:
            obj = Fashion.objects.select_related('product').get(pk=pk)
        except Fashion.DoesNotExist:
            return Response({"error": "Fashion not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(FashionSerializer(obj).data)

    def put(self, request, pk):
        try:
            obj = Fashion.objects.select_related('product').get(pk=pk)
        except Fashion.DoesNotExist:
            return Response({"error": "Fashion not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = FashionSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = Fashion.objects.select_related('product').get(pk=pk)
        except Fashion.DoesNotExist:
            return Response({"error": "Fashion not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def health_check(request):
    return JsonResponse({'status': 'healthy', 'service': 'product-service'})
