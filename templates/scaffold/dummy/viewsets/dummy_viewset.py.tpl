from rest_framework import status
from rest_framework.response import Response

from core.views.api.base_viewset import BaseModelViewSet

from dummy.serializers import (
    DummyRequestSerializer,
    DummyResponseSerializer,
)
from dummy.services import Service


class DummyViewSet(BaseModelViewSet):
    """CRUD viewset for Dummy.

    Lookup is by `uid` (UUID) — configured on `BaseModelViewSet`.
    All Cassandra queries live in `Service` / `Repository`.
    """

    serializer_class = DummyResponseSerializer

    def get_queryset(self):
        return Service().all()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                DummyResponseSerializer(page, many=True).data
            )
        return Response(DummyResponseSerializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        instance = Service().find(kwargs['uid'])
        return Response(DummyResponseSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = DummyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Service().create_dummy(
            owner_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(
            DummyResponseSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        serializer = DummyRequestSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = service.update(instance, **serializer.validated_data)
        return Response(DummyResponseSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
