import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.chat.services.conversation_service import ConversationService
from features.chat.services.conversation_member_service import ConversationMemberService
from features.chat.services.direct_service import (
    list_direct_conversations,
    create_message as svc_create_message,
    mark_conversation_seen,
)

logger = logging.getLogger(__name__)


def _broadcast_direct_message(conversation_uid: str, payload: dict) -> None:
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f'chat_{conversation_uid}',
            {'type': 'broadcast_message', **payload},
        )
    except Exception as exc:
        logger.warning('Failed to broadcast direct message to WS group: %s', exc)


class DirectConversationViewSet(UserScopeMixin, ViewSet):

    def list(self, request):
        data = list_direct_conversations(request.user.uid)
        return Response(data)

    @action(detail=False, methods=['post'], url_path='lookup-by-target')
    def lookup_by_target(self, request):
        target_user_id = request.data.get('target_user_id')
        if not target_user_id:
            return Response({'error': 'target_user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        from features.chat.services.direct_service import find_conversation_with_target
        result = find_conversation_with_target(request.user.uid, uuid.UUID(str(target_user_id)))
        if result is None:
            return Response({'conversation_uid': None}, status=status.HTTP_200_OK)
        return Response({'conversation_uid': str(result.uid), 'other_user': result['other_user']})

    def create(self, request):
        target_user_id = request.data.get('target_user_id')
        if not target_user_id:
            return Response({'error': 'target_user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if str(target_user_id) == str(request.user.uid):
            return Response({'error': 'Cannot create DM with yourself'}, status=status.HTTP_400_BAD_REQUEST)

        conv_svc = ConversationService()
        conv, created = conv_svc.get_or_create_direct(
            user_a_id=request.user.uid,
            user_b_id=uuid.UUID(str(target_user_id)),
        )

        member_svc = ConversationMemberService()
        member_svc.add_member(conv.uid, request.user)
        from features.account.consumer.models import Consumer
        from features.account.space.models import Space
        try:
            target = Consumer.objects.get(uid=uuid.UUID(str(target_user_id)))
        except Exception:
            try:
                target = Space.objects.get(uid=uuid.UUID(str(target_user_id)))
            except Exception:
                target = None
        if target is not None:
            member_svc.add_member(conv.uid, target)

        return Response({
            'conversation_uid': str(conv.uid),
            'type': conv.type,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DirectMessageViewSet(UserScopeMixin, ViewSet):

    def create(self, request):
        conversation_uid = request.data.get('conversation_uid')
        content = request.data.get('content', '') or ''
        msg_type = request.data.get('msg_type', 'text') or 'text'
        resource_uid = request.data.get('resource_uid')
        resource_url = request.data.get('resource_url', '') or ''
        resource_name = request.data.get('resource_name', '') or ''
        resource_size = int(request.data.get('resource_size') or 0)

        if not conversation_uid:
            return Response({'error': 'conversation_uid is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not content and not resource_url:
            return Response({'error': 'content or attachment required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sender_type = 'space' if hasattr(request.user, 'logo_url') else 'consumer'
            sender_name = (
                getattr(request.user, 'full_name', '')
                or getattr(request.user, 'name', '')
                or getattr(request.user, 'username', '')
                or ''
            )
            msg = svc_create_message(
                conversation_uid=conversation_uid,
                sender_id=request.user.uid,
                sender_name=sender_name,
                sender_type=sender_type,
                content=content,
                msg_type=msg_type,
                resource_uid=resource_uid,
                resource_url=resource_url,
                resource_name=resource_name,
                resource_size=resource_size,
            )
            _broadcast_direct_message(str(conversation_uid), {
                'uid': msg['uid'],
                'conversation_uid': msg['conversation_uid'],
                'msg_type': msg['msg_type'],
                'content': msg.get('content', ''),
                'sender_id': msg.get('sender_id'),
                'sender_type': msg.get('sender_type', ''),
                'sender_name': msg.get('sender_name', ''),
                'resource_uid': (msg.get('attachment') or {}).get('uid'),
                'resource_url': (msg.get('attachment') or {}).get('url', ''),
                'resource_name': (msg.get('attachment') or {}).get('name', ''),
                'resource_size': (msg.get('attachment') or {}).get('size', 0),
                'created_at': msg.get('created_at') or '',
            })
            return Response(msg, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Send failed: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='seen')
    def seen(self, request):
        conversation_uid = request.data.get('conversation_uid')
        msg_uid = request.data.get('msg_uid')
        if not conversation_uid:
            return Response({'error': 'conversation_uid is required'}, status=status.HTTP_400_BAD_REQUEST)
        mark_conversation_seen(conversation_uid, request.user.uid, msg_uid)
        return Response({'message': 'marked as seen'})
