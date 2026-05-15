from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from core.serializers.classroom import ClassroomResponseSerializer
from core.serializers.classroom.request import ClassroomRequestSerializer
from features.course.classroom.services import Service
from features.account.space.models.space import Space
from features.sharing.services import LinkService
from features.sharing.serializers.link_response_serializer import LinkResponseSerializer

class ClassroomViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = ClassroomResponseSerializer

    def get_queryset(self):
        return Service().get_active_classrooms()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = Service().find(kwargs['uid'])
        return Response(ClassroomResponseSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        # Only teachers (Space accounts) can create a classroom
        if not isinstance(request.user, Space):
            raise PermissionDenied("Only teachers (Space accounts) can create a classroom.")

        serializer = ClassroomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Service().create_classroom(
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(ClassroomResponseSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        
        # Ownership check
        if not isinstance(request.user, Space) or instance.teacher_id != request.user.uid:
            raise PermissionDenied("You do not have permission to update this classroom.")

        serializer = ClassroomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = service.update(instance, **serializer.validated_data)
        return Response(ClassroomResponseSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        
        # Ownership check
        if not isinstance(request.user, Space) or instance.teacher_id != request.user.uid:
            raise PermissionDenied("You do not have permission to delete this classroom.")

        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def sharing_link(self, request, uid=None):
        classroom = Service().find(uid)
        link_service = LinkService()
        
        # Find link by resource_id
        links = link_service.repository.get_by_resource('classroom', classroom.uid)
        link = links.first() if links else None
        
        if not link:
            # Fallback: create one if missing for some reason
            link = link_service.create_link({
                'code': classroom.pid,
                'resource_type': 'classroom',
                'resource_id': classroom.uid,
                'action': 'join',
                'metadata': {'name': classroom.name}
            })

        # Lazy load QR
        link_service.get_or_create_qr_code(link)
        
        return Response(LinkResponseSerializer(link).data)
