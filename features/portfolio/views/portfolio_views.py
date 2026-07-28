import os
import uuid
import json
import mimetypes
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from core.storages.storage_service import storage_service
from features.portfolio.models import Portfolio
from features.portfolio.serializers import (
    PortfolioBulkUpdateSerializer,
    PortfolioEntrySerializer,
    PortfolioReorderBulkSerializer,
    PortfolioUploadResponseSerializer,
)
from features.portfolio.services import PortfolioService


def _serialize_entry(instance):
    try:
        value = json.loads(instance.value) if instance.value else {}
    except (TypeError, json.JSONDecodeError):
        value = {}
    return {
        'uid': str(instance.uid),
        'key': instance.key,
        'value': value,
        'is_public': instance.is_public,
        'display_order': instance.display_order,
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
        'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
    }


def _normalize_payload(request):
    if hasattr(request.data, 'lists'):
        data = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in request.data.lists()}
    elif hasattr(request.data, 'copy'):
        data = dict(request.data.copy())
    else:
        data = dict(request.data)
    if 'value' in data and isinstance(data['value'], str):
        try:
            data['value'] = json.loads(data['value'])
        except (TypeError, json.JSONDecodeError):
            raise ValidationError({'value': 'value must be valid JSON.'})
    file_obj = request.FILES.get('file') if hasattr(request, 'FILES') else None
    if file_obj is not None:
        image_field = data.get('image_field') or 'image'
        owner_id = str(request.user.uid)
        ext = os.path.splitext(file_obj.name)[1]
        object_key = f"portfolio/{owner_id}/{uuid.uuid4()}{ext}"
        result = storage_service.upload_fileobj(file_obj, object_key, is_public=True)
        if not result.get('success'):
            raise ValidationError({'file': result.get('message', 'Upload failed.')})
        if not isinstance(data.get('value'), dict):
            data['value'] = {}
        data['value'][image_field] = result.get('url', '')
        data['value']['file_key'] = result.get('object_key', object_key)
        data['value']['file_type'] = file_obj.content_type or mimetypes.guess_type(file_obj.name)[0] or ''
        data['value']['file_name'] = file_obj.name
        data.pop('image_field', None)
    return data


class MyPortfolioView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        service = PortfolioService()
        data = service.get_mine(request.user)
        return Response(data)

    def patch(self, request):
        serializer = PortfolioBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = PortfolioService()
        result = service.bulk_upsert(request.user, serializer.validated_data['entries'])
        return Response(result)


class PortfolioEntryDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request, uid):
        data = _normalize_payload(request)
        data.pop('uid', None)
        serializer = PortfolioEntrySerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['uid'] = uid
        service = PortfolioService()
        instance = service.upsert_entry(request.user, serializer.validated_data)
        return Response(_serialize_entry(instance))

    def delete(self, request, uid):
        service = PortfolioService()
        service.delete_entry(request.user, uid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioEntryCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = _normalize_payload(request)
        serializer = PortfolioEntrySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        service = PortfolioService()
        instance = service.upsert_entry(request.user, serializer.validated_data)
        return Response(_serialize_entry(instance), status=status.HTTP_201_CREATED)


class PortfolioReorderView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def patch(self, request):
        serializer = PortfolioReorderBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = PortfolioService()
        result = service.reorder(request.user, serializer.validated_data['orders'])
        return Response(result)


class PortfolioUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response(
                {'success': False, 'message': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_obj = request.FILES['file']
        owner_id = str(request.user.uid)
        ext = os.path.splitext(file_obj.name)[1]
        object_key = f"portfolio/{owner_id}/{uuid.uuid4()}{ext}"
        result = storage_service.upload_fileobj(file_obj, object_key, is_public=True)
        if not result.get('success'):
            return Response(
                {'success': False, 'message': result.get('message', 'Upload failed.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = {
            'file_key': result['object_key'],
            'url': result.get('url', ''),
        }
        return Response(
            PortfolioUploadResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )


class PublicPortfolioView(APIView):
    permission_classes = []

    def get(self, request, owner_type, owner_id):
        if owner_type not in Portfolio.OWNER_TYPES:
            raise NotFound('Invalid owner type.')
        service = PortfolioService()
        data = service.get_public(owner_type, owner_id)
        return Response(data)
