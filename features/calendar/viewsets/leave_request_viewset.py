from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.leave_request_service import LeaveRequestService
from features.calendar.serializers.leave_request_serializer import LeaveRequestSerializer, LeaveRequestProcessSerializer

class LeaveRequestViewSet(UserScopeMixin, ViewSet):
    def list(self, request):
        status_filter = request.query_params.get('status')
        service = LeaveRequestService()
        if status_filter == 'pending':
            requests = service.repository.get_pending_requests(request.user.uid)
        else:
            requests = service.repository.get_by_space(request.user.uid)
            
        return Response(LeaveRequestSerializer(requests, many=True).data)

    @action(detail=True, methods=['post'], url_path='process')
    def process(self, request, pk=None):
        serializer = LeaveRequestProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_request = LeaveRequestService().process_request(
            request_uid=pk,
            teacher_id=request.user.uid,
            **serializer.validated_data
        )
        return Response(LeaveRequestSerializer(updated_request).data)
