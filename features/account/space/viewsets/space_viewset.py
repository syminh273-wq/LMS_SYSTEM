from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import os

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.space.serializers import SpaceAccountSerializer, SpaceAccountCreateSerializer, SpaceAccountUpdateSerializer
from features.account.space.services import Service
from features.account.space.repositories import Repository


class ViewSet(UserScopeMixin, BaseModelViewSet):
    repository = Repository()
    queryset = repository.all()
    serializer_class = SpaceAccountSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request, *args, **kwargs):
        """
        Listing spaces
        """
        service = Service()
        self.queryset = service.get_active_spaces()
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request, *args, **kwargs):
        """
        Get current space profile
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(SpaceAccountSerializer(instance=request.user).data)

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request, *args, **kwargs):
        """
        Get current space profile
        """
        return self.me(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a space detail
        """
        instance = self.get_object()
        serializer = SpaceAccountSerializer(instance=instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new space account
        """
        serializer = SpaceAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = Service()
        # Note: SpaceService.register handles the logic
        space = service.register(serializer.validated_data)

        serialize_data = SpaceAccountSerializer(instance=space)
        return Response(serialize_data.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Update a space
        """
        data = request.data.copy()
        instance = self.get_object()
        user_uid = str(instance.uid)

        from core.storages.storage_service import storage_service

        # Handle logo upload
        if 'logo' in request.FILES:
            logo_file = request.FILES['logo']
            ext = os.path.splitext(logo_file.name)[1]
            unique_filename = f"spaces/logos/{user_uid}{ext}"
            res = storage_service.upload_fileobj(logo_file, unique_filename, is_public=True)
            if res['success']:
                data['logo_url'] = res['object_key']

        # Handle cover upload
        if 'cover' in request.FILES:
            cover_file = request.FILES['cover']
            ext = os.path.splitext(cover_file.name)[1]
            unique_filename = f"spaces/covers/{user_uid}{ext}"
            res = storage_service.upload_fileobj(cover_file, unique_filename, is_public=True)
            if res['success']:
                data['cover_url'] = res['object_key']

        serializer = SpaceAccountUpdateSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = Service()
        instance = service.update(instance, **serializer.validated_data)

        serialize_data = SpaceAccountSerializer(instance=instance)
        return Response(serialize_data.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a space
        """
        return super().destroy(request, *args, **kwargs)
