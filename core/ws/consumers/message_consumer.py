from .base_consumer import BaseWebSocketConsumer

class MessageConsumer(BaseWebSocketConsumer):
    """
    Consumer for Chat/Messaging functionality.
    """
    
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name', 'default')
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def handle_message(self, data):
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            message = data.get('message')
            sender = data.get('sender')
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_handler',
                    'message': message,
                    'sender': sender
                }
            )
        else:
            await self.send_error(f"Unknown message type: {message_type}")

    # Receive message from room group
    async def chat_message_handler(self, event):
        message = event['message']
        sender = event['sender']

        # Send message to WebSocket
        await self.send_json({
            'type': 'chat_message',
            'message': message,
            'sender': sender
        })
