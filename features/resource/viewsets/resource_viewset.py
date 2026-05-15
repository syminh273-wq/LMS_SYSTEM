from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.resource.services.resource_service import ResourceService
from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer
from features.resource.serializers.resource_request_serializer import ResourceRequestSerializer
from features.resource.serializers.resource_query_serializer import ResourceQuerySerializer

class ResourceViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = ResourceResponseSerializer
    service = ResourceService()

    def get_queryset(self):
        # Default implementation: list all (might want to filter by user in production)
        return self.service.all()

    def list(self, request, *args, **kwargs):
        query_serializer = ResourceQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        file_type = query_serializer.validated_data.get('type')
        
        queryset = self.service.get_resources(
            owner_id=request.user.uid,
            file_type=file_type
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.service.find(kwargs['uid'])
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        if 'file' not in request.FILES:
            return Response({
                'success': False,
                'message': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['file']
        metadata = request.data.get('metadata', {})
        
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        # Allow caller to explicitly set owner_id / owner_type (e.g. classroom upload)
        import uuid as _uuid
        raw_owner_id = request.data.get('owner_id')
        raw_owner_type = request.data.get('owner_type')

        if raw_owner_id and raw_owner_type:
            try:
                owner_id = _uuid.UUID(str(raw_owner_id))
            except ValueError:
                return Response({'success': False, 'message': 'Invalid owner_id'}, status=status.HTTP_400_BAD_REQUEST)
            owner_type = raw_owner_type
        else:
            owner_id = request.user.uid if hasattr(request.user, 'uid') else None
            owner_type = None
            if request.user:
                from features.account.consumer.models.consumer import Consumer
                from features.account.space.models.space import Space
                if isinstance(request.user, Consumer):
                    owner_type = 'consumer'
                elif isinstance(request.user, Space):
                    owner_type = 'space'

        result = self.service.upload_resource(
            file_obj=file_obj,
            owner_id=owner_id,
            owner_type=owner_type,
            metadata=metadata
        )

        if result.get('success'):
            return Response(
                self.get_serializer(result['data']).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.service.find(kwargs['uid'])
        
        # Ownership check
        if instance.owner_id != request.user.uid:
            raise PermissionDenied("You do not have permission to update this resource.")

        serializer = ResourceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_instance = self.service.update(instance, **serializer.validated_data)
        return Response(self.get_serializer(updated_instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.service.find(kwargs['uid'])
        
        # Ownership check
        if instance.owner_id != request.user.uid:
            raise PermissionDenied("You do not have permission to delete this resource.")

        # Optional: Delete from R2 as well?
        # For now just soft delete from DB
        self.service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
