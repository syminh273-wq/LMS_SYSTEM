from datetime import datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.calendar.services.calendar_service import CalendarService
from features.calendar.serializers.calendar_serializer import CalendarEventSerializer, CalendarEventCreateSerializer


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None


class CalendarViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = CalendarEventSerializer

    def get_queryset(self):
        return CalendarService().get_events(
            space_id=self.request.user.uid,
            classroom_id=self.request.query_params.get('classroom_id'),
            start_date=_parse_dt(self.request.query_params.get('start_date')),
            end_date=_parse_dt(self.request.query_params.get('end_date')),
        )

    def list(self, request, *args, **kwargs):
        events = self.get_queryset()
        type_ = request.query_params.get('type')
        if type_:
            events = [e for e in events if e.type == type_]
        context = {'classroom_name_cache': {}}
        return Response(CalendarEventSerializer(list(events), many=True, context=context).data)

    def create(self, request, *args, **kwargs):
        serializer = CalendarEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = CalendarService().create_event(
            space_id=request.user.uid,
            owner_id=request.user.uid,
            **serializer.validated_data
        )
        return Response(
            CalendarEventSerializer(event, context={'classroom_name_cache': {}}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        service = CalendarService()
        event = service.find(kwargs['uid'])

        if str(event.owner_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền cập nhật sự kiện này.")

        serializer = CalendarEventCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        instance = service.update_event(event, request.user.uid, **serializer.validated_data)
        return Response(
            CalendarEventSerializer(instance, context={'classroom_name_cache': {}}).data
        )

    def destroy(self, request, *args, **kwargs):
        service = CalendarService()
        event = service.find(kwargs['uid'])

        if str(event.owner_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xoá sự kiện này.")

        service.delete_event(event, request.user.uid)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        service = CalendarService()
        event = service.find(kwargs['uid'])
        if str(event.owner_id) != str(request.user.uid):
            raise PermissionDenied("Bạn không có quyền xem sự kiện này.")
        return Response(
            CalendarEventSerializer(event, context={'classroom_name_cache': {}}).data
        )
