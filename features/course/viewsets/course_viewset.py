from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.serializers.course import CourseResponseSerializer, CourseEnrollmentResponseSerializer
from core.serializers.course.request import CourseRequestSerializer
from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.space.models.space import Space
from features.course.services import CourseService, CourseEnrollmentService
from features.sharing.services import LinkService
from features.sharing.serializers.link_response_serializer import LinkResponseSerializer


class CourseViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = CourseResponseSerializer

    def get_queryset(self):
        course_service = CourseService()
        if isinstance(self.request.user, Space):
            return course_service.get_by_teacher(self.request.user.uid)
        return course_service.get_published_courses()

    def list(self, request, *args, **kwargs):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể xem danh sách khóa học.")
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể xem chi tiết khóa học.")
        course_service = CourseService()
        instance = course_service.find(kwargs['uid'])
        if str(instance.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xem khóa học này.")
        return Response(CourseResponseSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        if not isinstance(request.user, Space):
            raise PermissionDenied("Chỉ giáo viên mới có thể tạo khóa học.")

        serializer = CourseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = CourseService().create_course(
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(CourseResponseSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        course_service = CourseService()
        instance = course_service.find(kwargs['uid'])
        if not isinstance(request.user, Space) or str(instance.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền cập nhật khóa học này.")

        serializer = CourseRequestSerializer(data=request.data, partial=(request.method == 'PATCH'))
        serializer.is_valid(raise_exception=True)
        instance = course_service.update(instance, **serializer.validated_data)
        return Response(CourseResponseSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        course_service = CourseService()
        instance = course_service.find(kwargs['uid'])
        if not isinstance(request.user, Space) or str(instance.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xóa khóa học này.")
        course_service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def publish(self, request, uid=None):
        course_service = CourseService()
        instance = course_service.find(uid)
        if not isinstance(request.user, Space) or str(instance.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xuất bản khóa học này.")
        try:
            updated = course_service.publish(instance)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CourseResponseSerializer(updated).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, uid=None):
        course_service = CourseService()
        instance = course_service.find(uid)
        if not isinstance(request.user, Space) or str(instance.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền hủy xuất bản khóa học này.")
        updated = course_service.unpublish(instance)
        return Response(CourseResponseSerializer(updated).data)

    @action(detail=True, methods=['get'])
    def sharing_link(self, request, uid=None):
        course_service = CourseService()
        course = course_service.find(uid)
        if not isinstance(request.user, Space) or str(course.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xem liên kết chia sẻ.")

        link_service = LinkService()
        link = link_service.repository.get_by_resource('course', course.uid).first()
        if not link:
            link = link_service.create_link({
                'code': course.pid,
                'resource_type': 'course',
                'resource_id': course.uid,
                'action': 'preview',
                'metadata': {
                    'name': course.name,
                    'pricing_type': course.pricing_type,
                    'price_vnd': str(course.price_vnd or 0),
                    'cover_url': course.cover_url or '',
                },
            })
        link_service.get_or_create_qr_code(link)
        return Response(LinkResponseSerializer(link).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, uid=None):
        course_service = CourseService()
        course = course_service.find(uid)
        if not isinstance(request.user, Space) or str(course.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xem thống kê.")
        return Response(course_service.get_stats(course.uid))

    @action(detail=True, methods=['get'], url_path='enrollments')
    def list_enrollments(self, request, uid=None):
        course_service = CourseService()
        course = course_service.find(uid)
        if not isinstance(request.user, Space) or str(course.teacher_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xem danh sách học viên.")
        enrollments = CourseEnrollmentService().list_for_course(course.uid)
        return Response(CourseEnrollmentResponseSerializer(enrollments, many=True).data)
