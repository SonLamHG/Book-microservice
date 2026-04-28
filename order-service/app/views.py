from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem, SagaLog
from .serializers import OrderSerializer
import requests
import os
from .messaging import publish_event

CART_SERVICE_URL = "http://cart-service:8000"
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"


def log_saga_step(order, step, step_status, details=''):
    SagaLog.objects.create(order=order, step=step, status=step_status, details=details)


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

        # === SAGA STEP 1: Get cart items ===
        try:
            r = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/", timeout=5)
            if r.status_code != 200:
                return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
            cart_items = r.json()
        except requests.exceptions.RequestException:
            return Response({"error": "Cart service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not cart_items:
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # === SAGA STEP 2: Create order (PENDING) ===
        order = Order.objects.create(
            customer_id=customer_id,
            shipping_address=shipping_address,
            payment_method=payment_method,
            shipping_method=shipping_method,
        )
        log_saga_step(order, 'CREATE_ORDER', 'SUCCESS')

        # === SAGA STEP 3: Fetch product prices and create order items ===
        # cart item uses book_id column (legacy name, maps to product_id)
        total = 0
        order_items_data = []
        for item in cart_items:
            product_id = item.get('book_id') or item.get('product_id')
            try:
                pr = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/{product_id}/", timeout=5)
                if pr.status_code != 200:
                    log_saga_step(order, 'FETCH_PRODUCT_PRICE', 'FAILED', f"Product {product_id} not found")
                    order.status = 'CANCELLED'
                    order.save()
                    log_saga_step(order, 'COMPENSATE_ORDER', 'SUCCESS', 'Order cancelled due to product not found')
                    return Response({"error": f"Product {product_id} not found"}, status=status.HTTP_400_BAD_REQUEST)
                product_data = pr.json()
                price = float(product_data.get('price', 0))
            except requests.exceptions.RequestException:
                log_saga_step(order, 'FETCH_PRODUCT_PRICE', 'FAILED', 'Product service unavailable')
                order.status = 'CANCELLED'
                order.save()
                log_saga_step(order, 'COMPENSATE_ORDER', 'SUCCESS', 'Order cancelled due to service unavailable')
                return Response({"error": "Product service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            order_items_data.append({
                'book_id': product_id,  # keep column name for DB compatibility
                'quantity': item['quantity'],
                'price': price,
            })
            total += price * item['quantity']

        for oi in order_items_data:
            OrderItem.objects.create(order=order, **oi)

        order.total_amount = total
        order.save()
        log_saga_step(order, 'FETCH_PRODUCT_PRICE', 'SUCCESS', f'Total: {total}')

        # === SAGA STEP 4: Reserve payment ===
        payment_id = None
        try:
            pr = requests.post(
                f"{PAY_SERVICE_URL}/payments/",
                json={"order_id": order.id, "amount": str(total), "method": payment_method, "status": "RESERVED"},
                timeout=5,
            )
            if pr.status_code == 201:
                payment_id = pr.json().get('id')
                log_saga_step(order, 'RESERVE_PAYMENT', 'SUCCESS', f'Payment ID: {payment_id}')
            else:
                log_saga_step(order, 'RESERVE_PAYMENT', 'FAILED', 'Payment creation failed')
                order.status = 'CANCELLED'
                order.save()
                log_saga_step(order, 'COMPENSATE_ORDER', 'SUCCESS', 'Order cancelled due to payment failure')
                return Response({"error": "Payment reservation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except requests.exceptions.RequestException:
            log_saga_step(order, 'RESERVE_PAYMENT', 'FAILED', 'Pay service unavailable')
            order.status = 'CANCELLED'
            order.save()
            log_saga_step(order, 'COMPENSATE_ORDER', 'SUCCESS', 'Order cancelled due to pay service unavailable')
            return Response({"error": "Payment service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # === SAGA STEP 5: Reserve shipment ===
        shipment_id = None
        try:
            sr = requests.post(
                f"{SHIP_SERVICE_URL}/shipments/",
                json={"order_id": order.id, "address": shipping_address, "method": shipping_method, "status": "RESERVED"},
                timeout=5,
            )
            if sr.status_code == 201:
                shipment_id = sr.json().get('id')
                log_saga_step(order, 'RESERVE_SHIPMENT', 'SUCCESS', f'Shipment ID: {shipment_id}')
            else:
                log_saga_step(order, 'RESERVE_SHIPMENT', 'FAILED', 'Shipment creation failed')
                if payment_id:
                    try:
                        requests.put(f"{PAY_SERVICE_URL}/payments/{payment_id}/cancel/", timeout=5)
                        log_saga_step(order, 'COMPENSATE_PAYMENT', 'SUCCESS', f'Payment {payment_id} cancelled')
                    except requests.exceptions.RequestException:
                        log_saga_step(order, 'COMPENSATE_PAYMENT', 'FAILED', 'Could not cancel payment')
                order.status = 'CANCELLED'
                order.save()
                log_saga_step(order, 'COMPENSATE_ORDER', 'SUCCESS', 'Order cancelled due to shipment failure')
                return Response({"error": "Shipment reservation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except requests.exceptions.RequestException:
            log_saga_step(order, 'RESERVE_SHIPMENT', 'FAILED', 'Ship service unavailable')
            if payment_id:
                try:
                    requests.put(f"{PAY_SERVICE_URL}/payments/{payment_id}/cancel/", timeout=5)
                    log_saga_step(order, 'COMPENSATE_PAYMENT', 'SUCCESS', f'Payment {payment_id} cancelled')
                except requests.exceptions.RequestException:
                    log_saga_step(order, 'COMPENSATE_PAYMENT', 'FAILED', 'Could not cancel payment')
            order.status = 'CANCELLED'
            order.save()
            log_saga_step(order, 'COMPENSATE_ORDER', 'SUCCESS', 'Order cancelled due to ship service unavailable')
            return Response({"error": "Shipping service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # === SAGA STEP 6: Confirm order ===
        order.status = 'CONFIRMED'
        order.save()
        log_saga_step(order, 'CONFIRM_ORDER', 'SUCCESS')

        # Publish order.created event
        publish_event('order.created', {
            'order_id': order.id,
            'customer_id': customer_id,
            'total_amount': str(total),
            'payment_id': payment_id,
            'shipment_id': shipment_id,
        })

        # Clear cart (non-critical)
        try:
            requests.delete(f"{CART_SERVICE_URL}/carts/{customer_id}/clear/", timeout=5)
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

        publish_event('order.status_changed', {
            'order_id': order.id,
            'status': order.status,
        })

        serializer = OrderSerializer(order)
        return Response(serializer.data)


def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({'status': 'healthy', 'service': 'order-service'})
