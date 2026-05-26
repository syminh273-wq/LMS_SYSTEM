from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.calendar_service import CalendarService
from features.calendar.serializers.calendar_serializer import CalendarEventSerializer
from features.course.classroom.services.classroom_member_service import ClassroomMemberService

class ConsumerCalendarViewSet(UserScopeMixin, ViewSet):
    def list(self, request):
        # Get all classrooms student has joined
        classroom_uids = ClassroomMemberService().get_joined_classroom_uids(request.user.uid)
        
        service = CalendarService()
        all_events = []
        for classroom_id in classroom_uids:
            events = service.get_events(space_id=None, classroom_id=classroom_id)
            all_events.extend(list(events))
            
        return Response(CalendarEventSerializer(all_events, many=True).data)
