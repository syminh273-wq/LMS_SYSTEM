from django.urls import re_path
from .consumers.message_consumer import MessageConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', MessageConsumer.as_asgi()),
]
