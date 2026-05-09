import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BaseWebSocketConsumer(AsyncWebsocketConsumer):
    """
    Base WebSocket Consumer for LMS_SYSTEM.
    Handles common logic like authentication, group management, etc.
    """
    
    async def connect(self):
        # We can implement JWT authentication here later
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            await self.handle_message(data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")

    async def handle_message(self, data):
        """Override this in child classes"""
        pass

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    async def send_error(self, message, code=400):
        await self.send_json({
            "type": "error",
            "message": message,
            "code": code
        })
