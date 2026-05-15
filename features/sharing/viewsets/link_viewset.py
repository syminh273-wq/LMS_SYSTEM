from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.views.api.base_viewset import BaseModelViewSet
from features.sharing.services import LinkService
from features.sharing.serializers.link_response_serializer import LinkResponseSerializer
from features.sharing.serializers.request.link_request_serializer import LinkRequestSerializer
from core.storages.storage_service import storage_service

class LinkViewSet(BaseModelViewSet):
    serializer_class = LinkResponseSerializer

    def get_queryset(self):
        return LinkService().all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        service = LinkService()
        instance = service.find(kwargs['uid'])
        
        # Lazy load QR Code
        service.get_or_create_qr_code(instance)
        
        return Response(self.get_serializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = LinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = LinkService().create_link(serializer.validated_data)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = LinkService().find(kwargs['uid'])
        serializer = LinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = LinkService().update(instance, **serializer.validated_data)
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = LinkService()
        instance = service.find(kwargs['uid'])
        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='resolve/(?P<code>[^/.]+)')
    def resolve(self, request, code=None):
        service = LinkService()
        link = service.get_by_code(code)
        if not link:
            return Response({'error': 'Link not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if active and not expired
        if not link.is_active:
             return Response({'error': 'Link is inactive'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Increment used count
        service.update(link, used_count=link.used_count + 1)

        # Lazy load QR Code
        service.get_or_create_qr_code(link)
        
        return Response(self.get_serializer(link).data)

    @action(detail=True, methods=['get'])
    def download_qr(self, request, uid=None):
        service = LinkService()
        link = service.find(uid)
        
        qr_url = service.get_or_create_qr_code(link)
        if not qr_url:
            return Response({'error': 'Could not generate QR code'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get object from R2
        object_key = f"qr_codes/{link.code}.png"
        result = storage_service.get_object(object_key, is_public=True)
        
        if not result['success']:
            return Response({'error': 'QR code file not found on storage'}, status=status.HTTP_404_NOT_FOUND)

        # Return as attachment
        response = HttpResponse(result['body'].read(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="qr_{link.code}.png"'
        return response
