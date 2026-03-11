from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Shipment
from .serializers import ShipmentSerializer


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
        serializer = ShipmentSerializer(shipment)
        return Response(serializer.data)
