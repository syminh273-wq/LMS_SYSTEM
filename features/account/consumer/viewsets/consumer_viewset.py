from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.consumer.serializers import ConsumerAccountSerializer, ConsumerAccountCreateSerializer, ConsumerAccountUpdateSerializer
from features.account.consumer.services import ConsumerService


class ViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = ConsumerAccountSerializer

    def get_queryset(self):
        return ConsumerService().get_active_consumers()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(ConsumerAccountSerializer(queryset, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        instance = ConsumerService().find(kwargs['uid'])
        return Response(ConsumerAccountSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = ConsumerAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Note: Depending on your application, creating a consumer via the standard API might or might not need a password.
        # Here we use the regular `create` method.
        instance = ConsumerService().create(**serializer.validated_data)
        return Response(ConsumerAccountSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = ConsumerService()
        instance = service.find(kwargs['uid'])
        serializer = ConsumerAccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = service.update(instance, **serializer.validated_data)
        return Response(ConsumerAccountSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = ConsumerService()
        instance = service.find(kwargs['uid'])
        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(ConsumerAccountSerializer(request.user).data)

    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate(self, request, *args, **kwargs):
        service = ConsumerService()
        instance = service.find(kwargs['uid'])
        return Response(ConsumerAccountSerializer(service.deactivate(instance)).data)
