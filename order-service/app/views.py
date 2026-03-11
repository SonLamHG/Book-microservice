from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem
from .serializers import OrderSerializer
import requests

CART_SERVICE_URL = "http://cart-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"


class OrderListCreate(APIView):
    def get(self, request):
        customer_id = request.query_params.get('customer_id')
        if customer_id:
            orders = Order.objects.filter(customer_id=customer_id)
        else:
            orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        customer_id = request.data.get('customer_id')
        shipping_address = request.data.get('shipping_address', '')
        payment_method = request.data.get('payment_method', 'COD')
        shipping_method = request.data.get('shipping_method', 'STANDARD')

        # Get cart items from cart-service
        try:
            r = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=5)
            if r.status_code != 200:
                return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
            cart_items = r.json()
        except requests.exceptions.RequestException:
            return Response({"error": "Cart service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not cart_items:
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Create order
        order = Order.objects.create(
            customer_id=customer_id,
            shipping_address=shipping_address,
            payment_method=payment_method,
            shipping_method=shipping_method,
        )

        total = 0
        order_items_data = []
        for item in cart_items:
            # Get book price from book-service
            try:
                br = requests.get(f"{BOOK_SERVICE_URL}/books/{item['book_id']}/", timeout=5)
                if br.status_code != 200:
                    order.delete()
                    return Response(
                        {"error": f"Book {item['book_id']} not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                book_data = br.json()
                price = float(book_data.get('price', 0))
            except requests.exceptions.RequestException:
                order.delete()
                return Response(
                    {"error": "Book service unavailable"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            order_items_data.append({
                'book_id': item['book_id'],
                'quantity': item['quantity'],
                'price': price,
            })
            total += price * item['quantity']

        for oi in order_items_data:
            OrderItem.objects.create(order=order, **oi)

        order.total_amount = total
        order.save()

        # Trigger payment via pay-service
        try:
            requests.post(
                f"{PAY_SERVICE_URL}/payments/",
                json={
                    "order_id": order.id,
                    "amount": str(total),
                    "method": payment_method,
                },
                timeout=5,
            )
        except requests.exceptions.RequestException:
            pass

        # Trigger shipping via ship-service
        try:
            requests.post(
                f"{SHIP_SERVICE_URL}/shipments/",
                json={
                    "order_id": order.id,
                    "address": shipping_address,
                    "method": shipping_method,
                },
                timeout=5,
            )
        except requests.exceptions.RequestException:
            pass

        # Clear cart after successful order
        try:
            requests.delete(
                f"{CART_SERVICE_URL}/carts/{customer_id}/clear/", timeout=5
            )
        except requests.exceptions.RequestException:
            pass

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderDetail(APIView):
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        order.status = request.data.get('status', order.status)
        order.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)
