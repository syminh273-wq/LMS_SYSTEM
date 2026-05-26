from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.attendance_service import AttendanceService
from features.calendar.serializers.attendance_serializer import AttendanceSerializer

class ConsumerAttendanceViewSet(UserScopeMixin, ViewSet):
    def list(self, request):
        attendances = AttendanceService().get_user_attendance(request.user.uid)
        return Response(AttendanceSerializer(attendances, many=True).data)
