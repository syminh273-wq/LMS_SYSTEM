from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.leave_request_service import LeaveRequestService
from features.calendar.serializers.leave_request_serializer import LeaveRequestSerializer, LeaveRequestCreateSerializer

class ConsumerLeaveRequestViewSet(UserScopeMixin, ViewSet):
    def list(self, request):
        requests = LeaveRequestService().repository.get_by_student(request.user.uid)
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def create(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In a real app, we might need to find the space_id from the event_id or classroom_id
        # For simplicity here, we assume space_id is provided or inferred.
        # Let's try to get space_id from event if event_id is provided
        space_id = request.data.get('space_id')
        if not space_id and serializer.validated_data.get('event_id'):
            from features.calendar.services.calendar_service import CalendarService
            event = CalendarService().find(serializer.validated_data['event_id'])
            space_id = event.space_id
            
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        leave_request = LeaveRequestService().submit_request(
            student_id=request.user.uid,
            space_id=space_id,
            reason=serializer.validated_data['reason'],
            evidence_file=request.FILES.get('evidence'),
            event_id=serializer.validated_data.get('event_id'),
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date')
        )
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED)
