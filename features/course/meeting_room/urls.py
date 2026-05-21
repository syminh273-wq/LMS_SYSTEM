from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets.meeting_room_viewset import MeetingRoomViewSet

router = DefaultRouter()
router.register(r'', MeetingRoomViewSet, basename='meeting-room')

urlpatterns = [
    path('', include(router.urls)),
]
