from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.calendar.services.calendar_service import CalendarService
from features.calendar.serializers.calendar_serializer import CalendarEventSerializer, CalendarEventCreateSerializer

class CalendarViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = CalendarEventSerializer

    def get_queryset(self):
        return CalendarService().get_events(space_id=self.request.user.uid)

    def create(self, request, *args, **kwargs):
        serializer = CalendarEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        event = CalendarService().create_event(
            space_id=request.user.uid,
            owner_id=request.user.uid,
            **serializer.validated_data
        )
        return Response(CalendarEventSerializer(event).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = CalendarService()
        event = service.find(kwargs['uid'])
        
        if event.owner_id != request.user.uid:
            raise PermissionDenied("You do not have permission to update this event.")
            
        instance = service.update(event, **request.data)
        return Response(CalendarEventSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = CalendarService()
        event = service.find(kwargs['uid'])
        
        if event.owner_id != request.user.uid:
            raise PermissionDenied("You do not have permission to delete this event.")
            
        service.delete(event)
        return Response(status=status.HTTP_204_NO_CONTENT)
