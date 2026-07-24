import json
import logging
from django.contrib.auth.models import AnonymousUser
from .base_consumer import BaseWebSocketConsumer

logger = logging.getLogger(__name__)

class RTCConsumer(BaseWebSocketConsumer):
    """
    Consumer for WebRTC signaling.
    Relays offer, answer, and ice-candidates between peers in a room.
    Broadcasts peer-joined / peer-left so existing peers can re-negotiate.
    """

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name', '')
        self.room_group_name = f'rtc_{self.room_name}'
        self.user = self.scope.get('user', AnonymousUser())

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'rtc_message',
                'message': {
                    'type': 'peer-joined',
                    'peer': {
                        'channel_name': self.channel_name,
                        'user_uid': str(getattr(self.user, 'uid', '')),
                        'user_type': getattr(self.user, '__class__', type(self.user)).__name__.lower(),
                    },
                },
                'sender_channel_name': self.channel_name,
            },
        )

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'rtc_message',
                    'message': {
                        'type': 'peer-left',
                        'peer': {
                            'channel_name': self.channel_name,
                            'user_uid': str(getattr(self.user, 'uid', '')),
                        },
                    },
                    'sender_channel_name': self.channel_name,
                },
            )
        except Exception as e:
            logger.warning(f'[RTC] failed to broadcast peer-left: {e}')
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def handle_message(self, data):
        msg_type = data.get('type')

        if msg_type in ['offer', 'answer', 'ice-candidate', 'renegotiate']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'rtc_message',
                    'message': data,
                    'sender_channel_name': self.channel_name,
                },
            )
        else:
            await self.send_error(f'Unknown signaling type: {msg_type}')

    async def rtc_message(self, event):
        message = event['message']
        sender_channel_name = event['sender_channel_name']

        if self.channel_name != sender_channel_name:
            await self.send_json(message)
