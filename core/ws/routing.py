from django.urls import re_path
from .consumers.message_consumer import MessageConsumer
from .consumers.rtc_consumer import RTCConsumer
from .consumers.attendance_consumer import AttendanceConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>[0-9a-f-]+)/$', MessageConsumer.as_asgi()),
    re_path(r'ws/rtc/(?P<room_name>[0-9a-f-]+)/$', RTCConsumer.as_asgi()),
    re_path(r'ws/presence/$', AttendanceConsumer.as_asgi()),
]
