from rest_framework import serializers
from .models import ChatSession, ChatMessage, CustomerBehaviorSummary, KnowledgeDocument


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'customer_id', 'created_at', 'is_active', 'messages']


class CustomerBehaviorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerBehaviorSummary
        fields = '__all__'


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = ['id', 'title', 'content', 'source', 'created_at']


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
