from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Shipment
from .serializers import ShipmentSerializer


def publish_event(event_type, data):
    try:
        import pika
        import json
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', connection_attempts=3, retry_delay=1))
        channel = connection.channel()
        channel.exchange_declare(exchange='bookstore', exchange_type='topic', durable=True)
        channel.basic_publish(exchange='bookstore', routing_key=event_type, body=json.dumps(data))
        connection.close()
    except Exception:
        pass


class ShipmentListCreate(APIView):
    def get(self, request):
        order_id = request.query_params.get('order_id')
        if order_id:
            shipments = Shipment.objects.filter(order_id=order_id)
        else:
            shipments = Shipment.objects.all()
        serializer = ShipmentSerializer(shipments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ShipmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShipmentDetail(APIView):
    def get(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk)
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShipmentSerializer(shipment)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk)
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)
        shipment.status = request.data.get('status', shipment.status)
        shipment.save()
        if shipment.status == 'SHIPPED':
            publish_event('shipment.shipped', {'shipment_id': shipment.id, 'order_id': shipment.order_id})
        serializer = ShipmentSerializer(shipment)
        return Response(serializer.data)


class CancelShipment(APIView):
    def put(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk)
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)
        shipment.status = 'CANCELLED'
        shipment.save()
        serializer = ShipmentSerializer(shipment)
        return Response(serializer.data)


def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({'status': 'healthy', 'service': 'ship-service'})
