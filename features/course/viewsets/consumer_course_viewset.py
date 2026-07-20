from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response

from core.serializers.course import (
    CourseResponseSerializer,
    CourseLessonResponseSerializer,
)
from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.consumer.models.consumer import Consumer
from features.course.services import (
    CourseService,
    CourseLessonService,
    CourseEnrollmentService,
)
from features.payment.services import PaymentService


class ConsumerCourseViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = CourseResponseSerializer

    def get_queryset(self):
        if isinstance(self.request.user, Consumer):
            return CourseService().get_published_courses()
        return CourseService().all()

    def list(self, request, *args, **kwargs):
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể xem danh sách khóa học.")
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể xem chi tiết khóa học.")
        course_service = CourseService()
        course = course_service.find(kwargs['uid'])
        enrollment_service = CourseEnrollmentService()
        if not enrollment_service.is_enrolled(request.user.uid, course.uid):
            raise PermissionDenied("Bạn chưa sở hữu khóa học này.")
        return Response(CourseResponseSerializer(course).data)

    @action(detail=False, methods=['get'], url_path='mine')
    def my_courses(self, request):
        """List courses the current consumer is enrolled in."""
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể xem khóa học của mình.")
        rows = CourseEnrollmentService().list_for_consumer(request.user.uid)
        # Hydrate and serialize
        result = []
        course_service = CourseService()
        for row in rows:
            try:
                course = course_service.find(row['enrollment'].course_uid)
                data = CourseResponseSerializer(course).data
                data['enrolled_at'] = row['enrollment'].enrolled_at
                data['pricing_type'] = row['enrollment'].pricing_type
                data['amount_vnd'] = int(row['enrollment'].amount_vnd or 0)
                result.append(data)
            except Exception:
                continue
        page = self.paginate_queryset(result)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='enroll')
    def enroll(self, request, uid=None):
        """Enroll in a FREE course. Returns { classroom_uid, redirect_to }."""
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể tham gia khóa học.")
        course_service = CourseService()
        try:
            course = course_service.find(uid)
        except Exception:
            raise NotFound('Không tìm thấy khóa học.')
        if course.status != 'published':
            raise PermissionDenied('Khóa học chưa được xuất bản.')
        try:
            result = CourseEnrollmentService().enroll_free(request.user, course)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='checkout')
    def checkout(self, request, uid=None):
        """Initiate MoMo payment for a PAID course."""
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể mua khóa học.")
        course_service = CourseService()
        try:
            course = course_service.find(uid)
        except Exception:
            raise NotFound('Không tìm thấy khóa học.')
        if course.status != 'published':
            raise PermissionDenied('Khóa học chưa được xuất bản.')
        if course.pricing_type != 'paid':
            return Response({'error': 'Khóa học này miễn phí, vui lòng dùng endpoint enroll.'}, status=status.HTTP_400_BAD_REQUEST)
        if int(course.price_vnd or 0) < 1000:
            return Response({'error': 'Giá khóa học không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = PaymentService().initiate(
                consumer_id=str(request.user.uid),
                amount=int(course.price_vnd),
                order_info=f'Khóa học: {course.name}',
                resource_type='course',
                resource_id=str(course.uid),
            )
        except Exception as e:
            return Response({'error': f'Khởi tạo thanh toán thất bại: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='access')
    def access(self, request, uid=None):
        """Poll endpoint used by checkout page to detect enrollment after IPN."""
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể kiểm tra quyền truy cập.")
        return Response(CourseEnrollmentService().get_access(str(request.user.uid), uid))

    @action(detail=True, methods=['get'], url_path='lessons')
    def list_lessons(self, request, uid=None):
        """List all published lessons of an enrolled course."""
        if not isinstance(request.user, Consumer):
            raise PermissionDenied("Chỉ sinh viên mới có thể xem bài học.")
        course_service = CourseService()
        enrollment_service = CourseEnrollmentService()
        try:
            course = course_service.find(uid)
        except Exception:
            raise NotFound('Không tìm thấy khóa học.')
        if not enrollment_service.is_enrolled(request.user.uid, course.uid):
            raise PermissionDenied("Bạn chưa sở hữu khóa học này.")
        lessons = CourseLessonService().list_published_lessons(course.uid)
        return Response(CourseLessonResponseSerializer(lessons, many=True).data)
