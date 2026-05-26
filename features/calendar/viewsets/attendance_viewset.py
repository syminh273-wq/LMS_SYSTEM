from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.attendance_service import AttendanceService
from features.calendar.serializers.attendance_serializer import AttendanceSerializer, AttendanceUpdateSerializer

class AttendanceViewSet(UserScopeMixin, ViewSet):
    def list(self, request):
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response({'error': 'event_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        attendances = AttendanceService().repository.get_by_event(event_id)
        return Response(AttendanceSerializer(attendances, many=True).data)

    @action(detail=False, methods=['patch'], url_path='update')
    def update_attendance(self, request):
        event_id = request.data.get('event_id')
        user_id = request.data.get('user_id')
        
        if not event_id or not user_id:
            return Response({'error': 'event_id and user_id are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = AttendanceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        attendance = AttendanceService().mark_attendance(
            event_id=event_id,
            user_id=user_id,
            status=serializer.validated_data['status']
        )
        return Response(AttendanceSerializer(attendance).data)
