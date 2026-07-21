import logging
import uuid

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views.api.pagination import StandardResultsSetPagination
from features.social.services.classroom_favorite_service import ClassroomFavoriteService

logger = logging.getLogger(__name__)


def _resolve_classroom(classroom_uid_raw):
    from features.course.classroom.repositories import Repository as ClassroomRepository
    try:
        uuid.UUID(classroom_uid_raw)
    except ValueError:
        return None, Response({'error': 'classroom_uid không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        classroom = ClassroomRepository().find(str(classroom_uid_raw))
    except Exception:
        return None, Response({'error': 'Lớp học không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)
    return classroom, None


class ClassroomFavoriteToggleView(APIView):
    """POST /api/v1/consumer/social/classrooms/{uid}/favorite/ — toggle on/off."""

    def post(self, request, classroom_uid=None):
        classroom, err = _resolve_classroom(classroom_uid)
        if err is not None:
            return err
        result = ClassroomFavoriteService().toggle(request.user.uid, classroom.uid)
        return Response(result)


class ClassroomFavoriteStatusView(APIView):
    """GET /api/v1/consumer/social/classrooms/{uid}/favorite/status/"""

    def get(self, request, classroom_uid=None):
        classroom, err = _resolve_classroom(classroom_uid)
        if err is not None:
            return err
        service = ClassroomFavoriteService()
        return Response({
            'is_favorited': service.is_favorited(request.user.uid, classroom.uid),
            'favorite_count': service.favorite_count(classroom.uid),
        })


class ClassroomFavoriteListView(APIView):
    """GET /api/v1/consumer/social/classrooms/favorites/ — paginated."""

    def get(self, request):
        service = ClassroomFavoriteService()
        favorites = service.list_for_consumer(request.user.uid)
        decorated = []
        for item in favorites:
            decorated.append({
                'classroom': item['classroom'],
                'created_at': item['created_at'],
            })
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(decorated, request)
        if page is not None:
            return paginator.get_paginated_response(service.serialize(page))
        return Response(service.serialize(decorated))
