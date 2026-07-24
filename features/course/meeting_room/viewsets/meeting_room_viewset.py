from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from features.course.meeting_room.services.meeting_room_service import MeetingRoomService
from features.course.meeting_room.services.meeting_room_participant_service import MeetingRoomParticipantService
from features.course.meeting_room.serializers.meeting_room_serializer import (
    MeetingRoomSerializer, CreateMeetingRoomRequest
)
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService
from features.course.classroom.services.classroom_member_service import ClassroomMemberService
from features.course.classroom.repositories import Repository as ClassroomRepository

class MeetingRoomViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MeetingRoomService()
        self.participant_service = MeetingRoomParticipantService()
        self.classroom_repo = ClassroomRepository()
        self.member_service = ClassroomMemberService()

    def _check_classroom_member(self, classroom_uid, user_uid):
        try:
            classroom = self.classroom_repo.find(str(classroom_uid))
        except Exception:
            return None
        if not classroom or getattr(classroom, 'is_deleted', False):
            return None
        if str(classroom.teacher_id) == str(user_uid):
            return classroom
        if not self.member_service.is_member(classroom.uid, user_uid):
            return None
        return classroom

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

        classroom_uid = serializer.validated_data.get('classroom_uid')
        if classroom_uid and not self._check_classroom_member(classroom_uid, request.user.uid):
            return Response(
                {"error": "Bạn không có quyền tạo phòng học cho lớp này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        room = self.service.create(request.user, serializer.validated_data)
        return Response(MeetingRoomSerializer(room).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def quick_start(self, request):
        serializer = CreateMeetingRoomRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        classroom_uid = serializer.validated_data.get('classroom_uid')
        if classroom_uid and not self._check_classroom_member(classroom_uid, request.user.uid):
            return Response(
                {"error": "Bạn không có quyền mở lớp học cho lớp này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        room = self.service.quick_start(request.user, serializer.validated_data)
        if room.classroom_uid:
            ClassroomActivityLogService().log(
                classroom_uid=room.classroom_uid,
                log_level='major',
                event_type='meeting_started',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=room.uid,
                target_name=room.title,
            )
        return Response(MeetingRoomSerializer(room).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='live')
    def live_room(self, request):
        classroom_uid = (request.query_params.get('classroom_uid') or '').strip()
        if not classroom_uid:
            return Response({"error": "classroom_uid is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not self._check_classroom_member(classroom_uid, request.user.uid):
            return Response(
                {"error": "Bạn chưa là thành viên của lớp học này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        marker = self.service.get_live_room(classroom_uid)
        if not marker:
            return Response({"live_room": None, "room": None})
        try:
            room = self.service.find(marker['room_uid'])
        except Exception:
            room = None
        if not room or room.status != 'active':
            self.service._clear_live_room_marker(classroom_uid, marker['room_uid'])
            return Response({"live_room": None, "room": None})
        return Response({
            "live_room": marker,
            "room": MeetingRoomSerializer(room).data,
        })

    def retrieve(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if room.classroom_uid and not self._check_classroom_member(room.classroom_uid, request.user.uid):
            return Response(
                {"error": "Bạn chưa là thành viên của lớp học này."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
    def join(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if room.classroom_uid and not self._check_classroom_member(room.classroom_uid, request.user.uid):
            return Response(
                {"error": "Bạn chưa là thành viên của lớp học này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if room.status == 'ended':
            return Response({"error": "Meeting has ended"}, status=status.HTTP_400_BAD_REQUEST)

        participant = self.participant_service.join(pk, request.user)
        self.service.repo.increment_participant(pk)
        return Response({
            "room": MeetingRoomSerializer(room).data,
            "participant_id": str(participant.participant_id),
            "camera_required": True,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)

        self.participant_service.leave(pk, request.user.uid)
        self.service.repo.decrement_participant(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        room = self.service.find(pk)
        if not room:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if str(room.host_id) != str(request.user.uid):
            return Response({"error": "Only host can end the meeting"}, status=status.HTTP_403_FORBIDDEN)

        room = self.service.update_status(room, 'ended')
        if room.classroom_uid:
            ClassroomActivityLogService().log(
                classroom_uid=room.classroom_uid,
                log_level='major',
                event_type='meeting_ended',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=room.uid,
                target_name=room.title,
            )
        return Response(MeetingRoomSerializer(room).data)
