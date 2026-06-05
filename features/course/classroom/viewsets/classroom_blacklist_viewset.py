from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.classroom.blacklist_serializer import BlacklistEntrySerializer, BlacklistRequestSerializer
from core.views.mixins import UserScopeMixin
from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService


class ClassroomBlacklistView(UserScopeMixin, APIView):
    """
    GET  /classrooms/{uid}/blacklist/              — list classroom-scoped blacklist
    POST /classrooms/{uid}/blacklist/              — add to classroom blacklist
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


class ClassroomBlacklistDetailView(UserScopeMixin, APIView):
    """
    DELETE /classrooms/{uid}/blacklist/{consumer_uid}/ — remove from classroom blacklist
    """

    def delete(self, request, uid=None, consumer_uid=None):
        ClassroomBlacklistService().remove_classroom_block(
            classroom_uid=uid,
            consumer_uid=consumer_uid,
            removed_by=request.user.uid,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class GlobalBlacklistView(UserScopeMixin, APIView):
    """
    GET  /api/v1/space/course/blacklist/   — list teacher's global blacklist
    POST /api/v1/space/course/blacklist/   — add to global blacklist
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
    DELETE /api/v1/space/course/blacklist/{consumer_uid}/ — remove from global blacklist
    """

    def delete(self, request, consumer_uid=None):
        ClassroomBlacklistService().remove_global_block(
            teacher_id=request.user.uid,
            consumer_uid=consumer_uid,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
