from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from features.account.space.serializers import PublicSpaceSerializer
from features.account.space.services import Service as SpaceService


class PublicTeacherView(APIView):
    permission_classes = []

    def get(self, request, uid):
        service = SpaceService()
        try:
            space = service.find(uid)
        except Exception:
            raise NotFound('Teacher not found.')

        if not getattr(space, 'is_active', True) or getattr(space, 'is_deleted', False):
            raise NotFound('Teacher not found.')

        serializer = PublicSpaceSerializer(instance=space)
        return Response(serializer.data, status=status.HTTP_200_OK)
