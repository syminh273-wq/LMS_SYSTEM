import uuid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from core.views.mixins import UserScopeMixin
from features.chat.services.message_service import MessageService
from features.chat.services.conversation_member_service import ConversationMemberService
from features.chat.serializers.message_serializer import MessageSerializer


class MessageViewSet(UserScopeMixin, ViewSet):

    def list(self, request):
        """GET /chat/messages/?conversation_uid=&limit=30&before_uid="""
        conversation_uid = request.query_params.get('conversation_uid')
        if not conversation_uid:
            return Response(
                {'error': 'conversation_uid query param is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = int(request.query_params.get('limit', 10))
            limit = min(max(limit, 1), 100)
        except (ValueError, TypeError):
            limit = 10

        before_uid = request.query_params.get('before_uid')
        service = MessageService()
        try:
            if before_uid:
                msgs = service.get_messages_before(
                    conversation_uid=conversation_uid,
                    before_uid=before_uid,
                    limit=limit,
                )
            else:
                msgs = service.get_messages(
                    conversation_uid=conversation_uid,
                    limit=limit,
                )
        except Exception:
            return Response(
                {'error': 'Invalid conversation_uid'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serialized = MessageSerializer(msgs, many=True).data
        return Response({
            'results': serialized,
            'has_more': len(msgs) == limit,
        })

    @action(detail=False, methods=['post'], url_path='read')
    def mark_read(self, request):
        """POST /chat/messages/read/ body={conversation_uid, msg_uid}"""
        conversation_uid = request.data.get('conversation_uid')
        msg_uid = request.data.get('msg_uid')
        if not conversation_uid or not msg_uid:
            return Response(
                {'error': 'conversation_uid and msg_uid are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ConversationMemberService().mark_read(
                conversation_uid=conversation_uid,
                member_id=request.user.uid,
                msg_uid=msg_uid,
            )
        except Exception:
            pass
        return Response({'message': 'marked'}, status=status.HTTP_200_OK)
