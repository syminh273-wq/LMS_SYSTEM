from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.course import CoursePreviewSerializer
from features.course.services import CourseService


class PublicCourseViewSet(APIView):
    """No-auth public endpoint to preview a course by its 6-char code."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, code=None):
        course_service = CourseService()
        try:
            data = course_service.get_public_preview(code)
        except Exception:
            return Response(
                {'error': 'Khóa học không tồn tại hoặc đã bị ẩn.'},
                status=404,
            )
        return Response(CoursePreviewSerializer(data).data)
