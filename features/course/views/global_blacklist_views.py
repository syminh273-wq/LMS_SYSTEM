from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.classroom.blacklist_serializer import BlacklistEntrySerializer, BlacklistRequestSerializer
from core.views.mixins import UserScopeMixin
from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService


class GlobalBlacklistView(UserScopeMixin, APIView):
    """
    List (GET) or add to (POST) a teacher's global (cross-classroom) blacklist.
    @param consumer_uid: student to block (POST, required)
    @param reason: block reason (POST, optional)
    @return: blacklist entries, or the created entry
    """

    def get(self, request):
        entries = ClassroomBlacklistService().list_global_blacklist(
            teacher_id=request.user.uid,
        )
        return Response(BlacklistEntrySerializer(entries, many=True).data)

    def post(self, request):
        serializer = BlacklistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = ClassroomBlacklistService().add_global_block(
            teacher_id=request.user.uid,
            consumer_uid=serializer.validated_data['consumer_uid'],
            reason=serializer.validated_data.get('reason', ''),
        )
        return Response(BlacklistEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class GlobalBlacklistDetailView(UserScopeMixin, APIView):
    """
    Remove a student from a teacher's global blacklist.
    @return: no content
    """

    def delete(self, request, consumer_uid=None):
        ClassroomBlacklistService().remove_global_block(
            teacher_id=request.user.uid,
            consumer_uid=consumer_uid,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
