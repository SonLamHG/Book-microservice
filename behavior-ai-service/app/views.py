from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .engine import BehaviorEngine


class BehaviorProfileView(APIView):
    def post(self, request):
        customer_id = request.data.get("customer_id")
        limit = int(request.data.get("limit", 10))
        exclude_recent_purchased = request.data.get("exclude_recent_purchased", True)
        if customer_id is None:
            return Response({"error": "customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        engine = BehaviorEngine()
        profile = engine.build_profile(
            int(customer_id),
            limit=max(1, min(limit, 20)),
            exclude_recent_purchased=bool(exclude_recent_purchased),
        )
        return Response(profile)


class BehaviorTrainView(APIView):
    def post(self, request):
        engine = BehaviorEngine()
        result = engine.train_model()
        status_code = status.HTTP_200_OK if result.get("trained") else status.HTTP_202_ACCEPTED
        payload = {key: value for key, value in result.items() if key != "model"}
        return Response(payload, status=status_code)


class BehaviorStatusView(APIView):
    def get(self, request):
        engine = BehaviorEngine()
        return Response(engine.get_status())


def health_check(request):
    return JsonResponse({"status": "healthy", "service": "behavior-ai-service"})
