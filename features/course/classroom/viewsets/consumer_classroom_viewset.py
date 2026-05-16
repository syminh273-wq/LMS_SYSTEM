import uuid

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from core.views.api.pagination import StandardResultsSetPagination
from core.serializers.classroom import ClassroomResponseSerializer
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_member_service import ClassroomMemberService
from features.chat.services.conversation_service import ConversationService
from features.chat.serializers.conversation_serializer import ConversationSerializer


class ConsumerClassroomViewSet(UserScopeMixin, ViewSet):
    """Classroom endpoints for students (Consumer accounts)."""

    pagination_class = StandardResultsSetPagination

    def list(self, request):
        """GET /api/v1/consumer/course/classrooms/ — chỉ trả về lớp đã tham gia."""
        uids = ClassroomMemberService().get_joined_classroom_uids(request.user.uid)
        service = Service()
        classrooms = []
        for uid in uids:
            try:
                classrooms.append(service.find(str(uid)))
            except Exception:
                continue
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(classrooms, request)
        if page is not None:
            return paginator.get_paginated_response(ClassroomResponseSerializer(page, many=True).data)
        return Response(ClassroomResponseSerializer(classrooms, many=True).data)

    def retrieve(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/"""
        instance = Service().find(pk)
        return Response(ClassroomResponseSerializer(instance).data)

    @action(detail=False, methods=['post'], url_path='join')
    def join_by_code(self, request):
        """POST /api/v1/consumer/course/classrooms/join/  body: {"code": "ABCDEF"}"""
        code = (request.data.get('code') or '').strip().upper()
        if not code:
            return Response({'error': 'Mã lớp không được để trống.'}, status=status.HTTP_400_BAD_REQUEST)

        from features.course.classroom.repositories import Repository
        classroom = Repository().filter(pid=code).first()
        if not classroom or getattr(classroom, 'is_deleted', False) or classroom.status != 'active':
            return Response({'error': 'Mã lớp không hợp lệ hoặc lớp không còn hoạt động.'}, status=status.HTTP_404_NOT_FOUND)

        ClassroomMemberService().join(classroom_uid=classroom.uid, user=request.user, role='student')
        return Response(ClassroomResponseSerializer(classroom).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def conversation(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/conversation/"""
        conv = ConversationService().get_or_create_channel(
            classroom_uid=uuid.UUID(str(pk)),
            created_by_id=request.user.uid,
        )
        return Response(ConversationSerializer(conv).data)
