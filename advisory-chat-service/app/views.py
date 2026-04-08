import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

from .models import ChatSession, ChatMessage, CustomerBehaviorSummary, KnowledgeDocument
from .serializers import (
    ChatSessionSerializer, ChatMessageSerializer,
    CustomerBehaviorSummarySerializer, KnowledgeDocumentSerializer,
    SendMessageSerializer,
)
from .behavior_analyzer import analyze_customer_behavior
from .chat_engine import generate_chat_response
from .knowledge_base import search_kb, embed_and_store_document

logger = logging.getLogger(__name__)


# ── Chat Endpoints ──────────────────────────────────────────────

class ChatSessionCreate(APIView):
    """POST /chat/sessions/ — Create a new chat session."""
    def post(self, request):
        customer_id = request.data.get('customer_id')
        if not customer_id:
            return Response({'error': 'customer_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        session = ChatSession.objects.create(customer_id=customer_id)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class ChatSessionDetail(APIView):
    """GET /chat/sessions/<session_id>/ — Get session with messages."""
    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(ChatSessionSerializer(session).data)


class ChatSendMessage(APIView):
    """POST /chat/sessions/<session_id>/messages/ — Send message and get AI response."""
    def post(self, request, session_id):
        try:
            session = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_message = serializer.validated_data['message']

        # Save user message
        ChatMessage.objects.create(session=session, role='user', content=user_message)

        # Generate AI response via RAG pipeline
        try:
            ai_response, context_used = generate_chat_response(session, user_message)
        except Exception as e:
            logger.error("Chat engine error: %s", e)
            ai_response = "Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại sau."
            context_used = None

        # Save assistant message
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_response,
            context_used=context_used,
        )

        return Response({
            'user_message': user_message,
            'assistant_message': ChatMessageSerializer(assistant_msg).data,
        })


# ── Behavior Endpoints ──────────────────────────────────────────

class BehaviorSummary(APIView):
    """GET /behavior/<customer_id>/ — Get behavior summary."""
    def get(self, request, customer_id):
        summary, created = CustomerBehaviorSummary.objects.get_or_create(
            customer_id=customer_id
        )
        if created:
            # First access → run analysis
            analyze_customer_behavior(customer_id)
            summary.refresh_from_db()

        return Response(CustomerBehaviorSummarySerializer(summary).data)


class BehaviorRefresh(APIView):
    """POST /behavior/<customer_id>/refresh/ — Force recalculate behavior."""
    def post(self, request, customer_id):
        analyze_customer_behavior(customer_id)
        summary = CustomerBehaviorSummary.objects.get(customer_id=customer_id)
        return Response(CustomerBehaviorSummarySerializer(summary).data)


# ── Knowledge Base Endpoints ────────────────────────────────────

class KBSearch(APIView):
    """GET /kb/search/?q=... — Search knowledge base."""
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'q parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        limit = int(request.query_params.get('limit', 3))
        results = search_kb(query, top_k=limit)
        return Response({'query': query, 'results': results})


class KBDocumentCreate(APIView):
    """POST /kb/documents/ — Add a KB document."""
    def post(self, request):
        title = request.data.get('title')
        content = request.data.get('content')
        source = request.data.get('source', 'faq')

        if not title or not content:
            return Response(
                {'error': 'title and content are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = embed_and_store_document(title, content, source)
        return Response(KnowledgeDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


# ── Health Check ────────────────────────────────────────────────

def health_check(request):
    return JsonResponse({'status': 'healthy', 'service': 'advisory-chat-service'})
