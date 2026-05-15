from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from core.views.mixins import UserScopeMixin
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_member_service import ClassroomMemberService


class ClassroomMemberViewSet(UserScopeMixin, ViewSet):

    def list(self, request, classroom_uid=None):
        """GET /classrooms/<uid>/members/"""
        members = ClassroomMemberService().get_members(classroom_uid)
        data = [
            {
                'member_id': str(m.member_id),
                'member_type': m.member_type,
                'member_name': m.member_name,
                'member_avatar': m.member_avatar or '',
                'role': m.role,
                'joined_at': m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ]
        return Response(data)

    @action(detail=False, methods=['post'])
    def join(self, request, classroom_uid=None):
        """POST /classrooms/<uid>/members/join/"""
        # Validate classroom exists
        classroom = Service().find(classroom_uid)
        member = ClassroomMemberService().join(
            classroom_uid=classroom.uid,
            user=request.user,
            role='student',
        )
        return Response({
            'member_id': str(member.member_id),
            'member_type': member.member_type,
            'member_name': member.member_name,
            'member_avatar': member.member_avatar or '',
            'role': member.role,
            'joined_at': member.joined_at.isoformat() if member.joined_at else None,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def leave(self, request, classroom_uid=None):
        """POST /classrooms/<uid>/members/leave/"""
        ClassroomMemberService().leave(
            classroom_uid=classroom_uid,
            member_id=request.user.uid,
        )
        return Response({'message': 'Left successfully'}, status=status.HTTP_200_OK)
