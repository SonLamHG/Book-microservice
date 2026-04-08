from django.urls import path
from . import views

urlpatterns = [
    # Chat endpoints
    path('chat/sessions/', views.ChatSessionCreate.as_view(), name='chat_session_create'),
    path('chat/sessions/<int:session_id>/', views.ChatSessionDetail.as_view(), name='chat_session_detail'),
    path('chat/sessions/<int:session_id>/messages/', views.ChatSendMessage.as_view(), name='chat_send_message'),

    # Behavior endpoints
    path('behavior/<int:customer_id>/', views.BehaviorSummary.as_view(), name='behavior_summary'),
    path('behavior/<int:customer_id>/refresh/', views.BehaviorRefresh.as_view(), name='behavior_refresh'),

    # Knowledge base endpoints
    path('kb/search/', views.KBSearch.as_view(), name='kb_search'),
    path('kb/documents/', views.KBDocumentCreate.as_view(), name='kb_document_create'),

    # Health
    path('health/', views.health_check, name='health_check'),
]
