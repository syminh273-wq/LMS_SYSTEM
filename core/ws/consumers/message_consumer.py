import logging
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .base_consumer import BaseWebSocketConsumer

logger = logging.getLogger(__name__)


class MessageConsumer(BaseWebSocketConsumer):
    """
    Consumer for Chat/Messaging functionality with JWT auth and DB persistence.
    """

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name', '')
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope.get('user', AnonymousUser())

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self._update_last_seen()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self._update_last_seen()

    async def handle_message(self, data):
        msg_type_event = data.get('type')

        if msg_type_event == 'chat_message':
            content = data.get('content', '')
            attachment = data.get('attachment') or {}

            msg_type = 'text'
            if attachment.get('url'):
                at = attachment.get('type', 'file')
                msg_type = at if at in ('image', 'video', 'audio', 'pdf', 'file') else 'file'

            message = await self._save_message(
                content=content,
                msg_type=msg_type,
                attachment=attachment,
            )
            if not message:
                await self.send_error('Failed to save message')
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'broadcast_message',
                    'uid': str(message.uid),
                    'conversation_uid': str(message.conversation_uid),
                    'msg_type': message.msg_type,
                    'content': message.content or '',
                    'sender_id': str(message.sender_id) if message.sender_id else None,
                    'sender_type': message.sender_type or '',
                    'sender_name': message.sender_name or '',
                    'resource_uid': str(message.resource_uid) if getattr(message, 'resource_uid', None) else None,
                    'resource_url': message.resource_url or '',
                    'resource_name': message.resource_name or '',
                    'resource_size': message.resource_size or 0,
                    'created_at': message.created_at.isoformat() if message.created_at else '',
                },
            )

        elif msg_type_event == 'typing_start':
            sender_name, _ = self._get_sender_info()
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'broadcast_typing',
                'sender_name': sender_name,
                'is_typing': True,
            })

        elif msg_type_event == 'typing_stop':
            sender_name, _ = self._get_sender_info()
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'broadcast_typing',
                'sender_name': sender_name,
                'is_typing': False,
            })

        elif msg_type_event == 'mark_read':
            msg_uid = data.get('msg_uid')
            if msg_uid:
                await self._mark_read(msg_uid)

        else:
            await self.send_error(f'Unknown type: {msg_type_event}')

    def _get_sender_info(self):
        user = self.user
        from features.account.space.models.space import Space
        from features.account.consumer.models.consumer import Consumer
        if isinstance(user, Space):
            name = user.full_name or user.name or user.email or 'Teacher'
            return name, 'space'
        elif isinstance(user, Consumer):
            name = user.full_name or user.username or user.email or 'Student'
            return name, 'consumer'
        return 'Unknown', 'unknown'

    @database_sync_to_async
    def _save_message(self, content, msg_type, attachment):
        try:
            from features.chat.services.message_service import MessageService
            service = MessageService()
            sender_name, sender_type = self._get_sender_info()
            return service.save_message(
                conversation_uid=self.room_name,
                sender_id=self.user.uid,
                sender_type=sender_type,
                sender_name=sender_name,
                msg_type=msg_type,
                content=content,
                resource_uid=attachment.get('uid'),
                resource_url=attachment.get('url', ''),
                resource_name=attachment.get('name', ''),
                resource_size=attachment.get('size', 0),
            )
        except Exception as e:
            logger.error(f"Save message error: {e}")
            return None

    @database_sync_to_async
    def _update_last_seen(self):
        try:
            if not self.room_name or isinstance(self.user, AnonymousUser):
                return
            from features.chat.services.conversation_member_service import ConversationMemberService
            ConversationMemberService().update_last_seen(self.room_name, self.user.uid)
        except Exception:
            pass

    @database_sync_to_async
    def _mark_read(self, msg_uid):
        try:
            from features.chat.services.conversation_member_service import ConversationMemberService
            ConversationMemberService().mark_read(self.room_name, self.user.uid, msg_uid)
        except Exception:
            pass

    async def broadcast_message(self, event):
        attachment = None
        if event.get('resource_url'):
            attachment = {
                'uid': event.get('resource_uid'),
                'url': event['resource_url'],
                'name': event.get('resource_name', ''),
                'size': event.get('resource_size', 0),
                'type': event['msg_type'],
            }
        await self.send_json({
            'type': 'chat_message',
            'uid': event['uid'],
            'conversation_uid': event['conversation_uid'],
            'msg_type': event['msg_type'],
            'content': event.get('content', ''),
            'sender_id': event.get('sender_id'),
            'sender_type': event.get('sender_type', ''),
            'sender_name': event.get('sender_name', ''),
            'attachment': attachment,
            'created_at': event['created_at'],
        })

    async def broadcast_typing(self, event):
        await self.send_json({
            'type': 'typing',
            'sender_name': event['sender_name'],
            'is_typing': event['is_typing'],
        })
