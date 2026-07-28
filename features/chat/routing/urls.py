from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.chat.viewsets import ConversationViewSet, MessageViewSet
from features.chat.viewsets.direct_viewset import DirectConversationViewSet, DirectMessageViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'direct/conversations', DirectConversationViewSet, basename='direct-conversation')
router.register(r'direct/messages', DirectMessageViewSet, basename='direct-message')

urlpatterns = [
    path('', include(router.urls)),
]
