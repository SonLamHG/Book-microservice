from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import AdvisorService, DEFAULT_PROMPT


class Recommendations(APIView):
    def get(self, request, customer_id):
        limit = int(request.query_params.get('limit', 5))
        user_prompt = request.query_params.get('prompt') or DEFAULT_PROMPT
        service = AdvisorService()
        return Response(service.recommend(customer_id, user_prompt=user_prompt, limit=limit))


class AdvisorRecommendations(APIView):
    def post(self, request):
        customer_id = request.data.get('customer_id')
        if customer_id is None:
            return Response({'error': 'customer_id is required'}, status=400)
        limit = int(request.data.get('limit', 3))
        user_prompt = request.data.get('user_prompt') or DEFAULT_PROMPT
        service = AdvisorService()
        return Response(service.recommend(int(customer_id), user_prompt=user_prompt, limit=limit))


def health_check(request):
    return JsonResponse({'status': 'healthy', 'service': 'recommender-ai-service'})
