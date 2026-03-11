from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import requests

BOOK_SERVICE_URL = "http://book-service:8000"


class CartCreate(APIView):
    def post(self, request):
        serializer = CartSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ViewCart(APIView):
    def get(self, request, customer_id):
        try:
            cart = Cart.objects.get(customer_id=customer_id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
        items = CartItem.objects.filter(cart=cart)
        serializer = CartItemSerializer(items, many=True)
        return Response(serializer.data)


class AddCartItem(APIView):
    def post(self, request):
        book_id = request.data.get("book_id")
        customer_id = request.data.get("customer_id")

        # Verify book exists via book-service
        try:
            r = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=5)
            if r.status_code != 200:
                return Response({"error": "Book not found"}, status=status.HTTP_404_NOT_FOUND)
        except requests.exceptions.RequestException:
            return Response({"error": "Book service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            cart = Cart.objects.get(customer_id=customer_id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            book_id=book_id,
            defaults={"quantity": request.data.get("quantity", 1)}
        )
        if not created:
            cart_item.quantity += request.data.get("quantity", 1)
            cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClearCart(APIView):
    def delete(self, request, customer_id):
        try:
            cart = Cart.objects.get(customer_id=customer_id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
        CartItem.objects.filter(cart=cart).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UpdateCartItem(APIView):
    def put(self, request, pk):
        try:
            item = CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        item.quantity = request.data.get("quantity", item.quantity)
        item.save()
        serializer = CartItemSerializer(item)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            item = CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
