from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.serializers.course import CourseLessonResponseSerializer
from core.serializers.course.request import CourseLessonRequestSerializer
from core.views.mixins import UserScopeMixin
from features.account.space.models.space import Space
from features.course.services import CourseLessonService


class CourseLessonViewSet(UserScopeMixin, ViewSet):
    """Nested under /space/course/courses/{course_uid}/lessons/"""

    def list(self, request, course_uid=None):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể xem danh sách bài học.")
        service = CourseLessonService()
        lessons = service.list_lessons(course_uid, teacher_id=request.user.uid)
        return Response(CourseLessonResponseSerializer(lessons, many=True).data)

    def create(self, request, course_uid=None):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể tạo bài học.")
        serializer = CourseLessonRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            lesson = CourseLessonService().create_lesson(
                course_uid, request.user.uid, serializer.validated_data
            )
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(CourseLessonResponseSerializer(lesson).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, course_uid=None, uid=None):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể xem bài học.")
        try:
            lesson = CourseLessonService().get_lesson(course_uid, uid, teacher_id=request.user.uid)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            raise NotFound('Không tìm thấy bài học.')
        return Response(CourseLessonResponseSerializer(lesson).data)

    def update(self, request, course_uid=None, uid=None):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể sửa bài học.")
        serializer = CourseLessonRequestSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            lesson = CourseLessonService().update_lesson(
                course_uid, uid, request.user.uid, serializer.validated_data
            )
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            raise NotFound('Không tìm thấy bài học.')
        return Response(CourseLessonResponseSerializer(lesson).data)

    def partial_update(self, request, course_uid=None, uid=None):
        return self.update(request, course_uid=course_uid, uid=uid)

    def destroy(self, request, course_uid=None, uid=None):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể xóa bài học.")
        try:
            CourseLessonService().delete_lesson(course_uid, uid, request.user.uid)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            raise NotFound('Không tìm thấy bài học.')
        return Response(status=status.HTTP_204_NO_CONTENT)

    def reorder(self, request, course_uid=None):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể sắp xếp bài học.")
        items = request.data.get('items') or []
        if not isinstance(items, list):
            return Response({'error': 'items phải là danh sách.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            lessons = CourseLessonService().reorder_lessons(course_uid, request.user.uid, items)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(CourseLessonResponseSerializer(lessons, many=True).data)
