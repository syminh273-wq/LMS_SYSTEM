from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.leave_request_service import LeaveRequestService
from features.calendar.serializers.leave_request_serializer import (
    LeaveRequestSerializer,
    LeaveRequestCreateSerializer,
)


class ConsumerLeaveRequestViewSet(UserScopeMixin, ViewSet):
    serializer_class = LeaveRequestSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def list(self, request):
        service = LeaveRequestService()
        classroom_id = request.query_params.get('classroom_id')
        if classroom_id:
            requests = service.list_for_classroom(classroom_id, student_id=request.user.uid)
        else:
            requests = service.repository.get_by_student(request.user.uid)
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def retrieve(self, request, pk=None):
        leave = LeaveRequestService().repository.find(pk)
        if str(leave.student_id) != str(request.user.uid):
            raise PermissionDenied('Bạn không có quyền xem đơn này.')
        return Response(LeaveRequestSerializer(leave).data)

    def create(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        space_id = request.data.get('space_id')
        if not space_id and data.get('event_id'):
            from features.calendar.services.calendar_service import CalendarService
            event = CalendarService().find(data['event_id'])
            space_id = event.space_id

        if not space_id:
            return Response({'error': 'space_id hoặc event_id là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)

        evidence_file = request.FILES.get('evidence')
        leave = LeaveRequestService().submit_request(
            student_id=request.user.uid,
            space_id=space_id,
            reason=data['reason'],
            evidence_file=evidence_file,
            event_id=data.get('event_id'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            classroom_id=data.get('classroom_id'),
        )
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        leave = LeaveRequestService().cancel_request(pk, request.user.uid)
        return Response(LeaveRequestSerializer(leave).data)
