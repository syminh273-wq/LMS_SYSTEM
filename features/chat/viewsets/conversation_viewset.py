import uuid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from core.views.mixins import UserScopeMixin
from features.chat.services.conversation_service import ConversationService
from features.chat.services.conversation_member_service import ConversationMemberService
from features.chat.serializers.conversation_serializer import ConversationSerializer


class ConversationViewSet(UserScopeMixin, ViewSet):

    def list(self, request):
        """GET /chat/conversations/?classroom_uid=<uid>"""
        classroom_uid = request.query_params.get('classroom_uid')
        if not classroom_uid:
            return Response(
                {'error': 'classroom_uid query param is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        service = ConversationService()
        # Auto-create channel if none exists
        conv = service.get_or_create_channel(
            classroom_uid=uuid.UUID(classroom_uid),
            created_by_id=request.user.uid if request.user else None,
        )
        convs = service.get_channels_by_classroom(uuid.UUID(classroom_uid))
        return Response(ConversationSerializer(convs, many=True).data)

    @action(detail=False, methods=['post'], url_path='channel')
    def create_channel(self, request):
        """POST /chat/conversations/channel/"""
        name = request.data.get('name', 'Thảo luận chung')
        classroom_uid = request.data.get('classroom_uid')
        if not classroom_uid:
            return Response(
                {'error': 'classroom_uid is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        service = ConversationService()
        conv = service.get_or_create_channel(
            classroom_uid=uuid.UUID(classroom_uid),
            name=name,
            created_by_id=request.user.uid,
        )
        return Response(ConversationSerializer(conv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='direct')
    def get_or_create_direct(self, request):
        """POST /chat/conversations/direct/ body={target_user_id}"""
        target_user_id = request.data.get('target_user_id')
        if not target_user_id:
            return Response(
                {'error': 'target_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        service = ConversationService()
        conv, created = service.get_or_create_direct(
            user_a_id=request.user.uid,
            user_b_id=uuid.UUID(str(target_user_id)),
        )
        # Add both users as members when first created
        if created:
            member_service = ConversationMemberService()
            member_service.add_member(conv.uid, request.user)
        resp_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(ConversationSerializer(conv).data, status=resp_status)
