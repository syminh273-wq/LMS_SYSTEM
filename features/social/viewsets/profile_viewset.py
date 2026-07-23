import os
import uuid

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.storages.storage_service import storage_service
from core.views.mixins import UserScopeMixin
from features.social.services.profile_service import ProfileService


def _upload_image(file_obj, owner_id: str, kind: str) -> dict:
    ext = os.path.splitext(file_obj.name)[1]
    object_key = f"profile/{owner_id}/{kind}/{uuid.uuid4()}{ext}"
    return storage_service.upload_fileobj(file_obj, object_key, is_public=True)


class MyProfileView(UserScopeMixin, APIView):
    parser_classes = [JSONParser]

    def get(self, request):
        data = ProfileService().get_mine(request.user)
        return Response(data)

    def patch(self, request):
        data = ProfileService().update_mine(request.user, request.data or {})
        return Response(data)


class PublicProfileView(UserScopeMixin, APIView):
    parser_classes = [JSONParser]

    def get(self, request, owner_id):
        data = ProfileService().get_public(owner_id)
        if not data:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)


class ProfileAvatarUploadView(UserScopeMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        result = _upload_image(request.FILES['file'], str(request.user.uid), 'avatar')
        if not result.get('success'):
            return Response({'error': result.get('message', 'Upload failed')}, status=status.HTTP_400_BAD_REQUEST)
        url = result.get('url', '')
        ProfileService().update_mine(request.user, {'avatar_url': url})
        return Response({'url': url, 'avatar_url': url}, status=status.HTTP_201_CREATED)


class ProfileCoverUploadView(UserScopeMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        result = _upload_image(request.FILES['file'], str(request.user.uid), 'cover')
        if not result.get('success'):
            return Response({'error': result.get('message', 'Upload failed')}, status=status.HTTP_400_BAD_REQUEST)
        url = result.get('url', '')
        ProfileService().update_mine(request.user, {'cover_url': url})
        return Response({'url': url, 'cover_url': url}, status=status.HTTP_201_CREATED)
