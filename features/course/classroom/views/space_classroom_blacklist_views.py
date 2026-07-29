from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.classroom.blacklist_serializer import BlacklistEntrySerializer, BlacklistRequestSerializer
from core.views.mixins import SpaceScopeMixin
from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService


class SpaceClassroomBlacklistView(SpaceScopeMixin, APIView):
    """
    List (GET) or add to (POST) a classroom's blacklist.
    @param consumer_uid: student to block (POST, required)
    @param reason: block reason (POST, optional)
    @return: blacklist entries, or the created entry
    """

    def get(self, request, uid=None):
        entries = ClassroomBlacklistService().list_classroom_blacklist(
            classroom_uid=uid,
            requested_by=request.user.uid,
        )
        return Response(BlacklistEntrySerializer(entries, many=True).data)

    def post(self, request, uid=None):
        serializer = BlacklistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        svc = ClassroomBlacklistService()
        entry = svc.add_classroom_block(
            classroom_uid=uid,
            consumer_uid=serializer.validated_data['consumer_uid'],
            added_by=request.user.uid,
            reason=serializer.validated_data.get('reason', ''),
        )
        # Auto-kick the member if they're still in the classroom
        try:
            from features.course.classroom.services.classroom_member_service import ClassroomMemberService
            ClassroomMemberService().kick(
                classroom_uid=uid,
                member_id=str(serializer.validated_data['consumer_uid']),
                kicked_by_id=request.user.uid,
            )
        except Exception:
            pass
        return Response(BlacklistEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class SpaceClassroomBlacklistDetailView(SpaceScopeMixin, APIView):
    """
    Remove a student from a classroom's blacklist.
    @return: no content
    """

    def delete(self, request, uid=None, consumer_uid=None):
        ClassroomBlacklistService().remove_classroom_block(
            classroom_uid=uid,
            consumer_uid=consumer_uid,
            removed_by=request.user.uid,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
