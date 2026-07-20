from datetime import datetime
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.calendar.services.calendar_service import CalendarService
from features.calendar.serializers.calendar_serializer import CalendarEventSerializer


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None


class ConsumerCalendarViewSet(UserScopeMixin, ViewSet):
    def list(self, request):
        events = CalendarService().get_for_consumer(
            member_id=request.user.uid,
            classroom_id=request.query_params.get('classroom_id'),
            start_date=_parse_dt(request.query_params.get('start_date')),
            end_date=_parse_dt(request.query_params.get('end_date')),
            type_=request.query_params.get('type'),
        )

        context = {'classroom_name_cache': {}}
        return Response(
            CalendarEventSerializer(list(events), many=True, context=context).data
        )

    def retrieve(self, request, uid=None):
        event = CalendarService().find(uid)
        from features.course.classroom.services.classroom_member_service import ClassroomMemberService
        if event.classroom_id and not ClassroomMemberService().is_member(event.classroom_id, request.user.uid):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Bạn không có quyền xem sự kiện này.")
        return Response(
            CalendarEventSerializer(event, context={'classroom_name_cache': {}}).data
        )
