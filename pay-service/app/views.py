from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payment
from .serializers import PaymentSerializer


class PaymentListCreate(APIView):
    def get(self, request):
        order_id = request.query_params.get('order_id')
        if order_id:
            payments = Payment.objects.filter(order_id=order_id)
        else:
            payments = Payment.objects.all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentDetail(APIView):
    def get(self, request, pk):
        try:
            payment = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            payment = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        payment.status = request.data.get('status', payment.status)
        payment.save()
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
