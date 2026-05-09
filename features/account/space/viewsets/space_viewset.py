from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.space.serializers import Serializer, CreateSerializer, UpdateSerializer
from features.account.space.services import Service


class ViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = Serializer

    def get_queryset(self):
        return Service().get_active_spaces()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(Serializer(queryset, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        instance = Service().find(kwargs['uid'])
        return Response(Serializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Service().create_space(
            owner_uid=request.user.pk,
            data=serializer.validated_data,
        )
        return Response(Serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        serializer = UpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = service.update(instance, **serializer.validated_data)
        return Response(Serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request, *args, **kwargs):
        spaces = Service().get_spaces_of_owner(request.user.pk)
        return Response(Serializer(spaces, many=True).data)

    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        return Response(Serializer(service.deactivate(instance)).data)
