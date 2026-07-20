from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.leave_request_service import LeaveRequestService
from features.calendar.serializers.leave_request_serializer import (
    LeaveRequestSerializer,
    LeaveRequestProcessSerializer,
)


class LeaveRequestViewSet(UserScopeMixin, ViewSet):
    serializer_class = LeaveRequestSerializer

    def _get_queryset(self, request):
        service = LeaveRequestService()
        status_filter = request.query_params.get('status')
        student_id = request.query_params.get('student_id')
        classroom_id = request.query_params.get('classroom_id')

        if student_id:
            requests = service.repository.get_by_space_student(request.user.uid, student_id)
        elif status_filter == 'pending':
            requests = service.repository.get_pending_requests(request.user.uid)
        elif status_filter:
            requests = [r for r in service.repository.get_by_space(request.user.uid) if r.status == status_filter]
        else:
            requests = service.repository.get_by_space(request.user.uid)

        if classroom_id:
            requests = self._filter_by_classroom(requests, classroom_id)

        return requests

    def _filter_by_classroom(self, requests, classroom_id):
        from features.calendar.repositories.calendar_event_repository import CalendarEventRepository

        event_repo = CalendarEventRepository()
        target = str(classroom_id)
        matching_event_ids = {
            str(e.uid) for e in event_repo.get_by_classroom(target) if e.uid is not None
        }
        return [r for r in requests if r.event_id and str(r.event_id) in matching_event_ids]

    def list(self, request):
        requests = self._get_queryset(request)
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def retrieve(self, request, pk=None):
        service = LeaveRequestService()
        leave = service.repository.find(pk)
        if str(leave.space_id) != str(request.user.uid):
            raise PermissionDenied('Bạn không có quyền xem đơn này.')
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=['post'], url_path='process')
    def process(self, request, pk=None):
        serializer = LeaveRequestProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = LeaveRequestService().process_request(
            request_uid=pk,
            teacher_id=request.user.uid,
            **serializer.validated_data,
        )
        return Response(LeaveRequestSerializer(updated).data)
