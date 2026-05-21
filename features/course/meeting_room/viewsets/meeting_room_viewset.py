from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from features.course.meeting_room.services.meeting_room_service import MeetingRoomService
from features.course.meeting_room.serializers.meeting_room_serializer import (
    MeetingRoomSerializer, CreateMeetingRoomRequest
)

class MeetingRoomViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MeetingRoomService()

    def list(self, request):
        classroom_uid = request.query_params.get('classroom_uid')
        if not classroom_uid:
            return Response({"error": "classroom_uid is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        rooms = self.service.get_by_classroom(classroom_uid)
        serializer = MeetingRoomSerializer(rooms, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = CreateMeetingRoomRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        room = self.service.create(request.user, serializer.validated_data)
        return Response(MeetingRoomSerializer(room).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(MeetingRoomSerializer(room).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if str(room.host_id) != str(request.user.uid):
            return Response({"error": "Only host can start the meeting"}, status=status.HTTP_403_FORBIDDEN)
        
        room = self.service.update_status(room, 'active')
        return Response(MeetingRoomSerializer(room).data)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        if str(room.host_id) != str(request.user.uid):
            return Response({"error": "Only host can end the meeting"}, status=status.HTTP_403_FORBIDDEN)
            
        room = self.service.update_status(room, 'ended')
        return Response(MeetingRoomSerializer(room).data)
