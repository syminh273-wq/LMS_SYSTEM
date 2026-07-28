from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views.mixins import UserScopeMixin
from features.social.services import PostService


class PostImageUploadView(UserScopeMixin, APIView):
    """
    Upload multiple post images to R2.
    @param files: multipart file list, field name 'files'
    @return: urls, errors, count
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'error': 'No files provided'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        urls, errors = PostService().upload_post_images(
            files=files,
            owner_id=str(request.user.uid),
        )
        return Response(
            {'urls': urls, 'errors': errors, 'count': len(urls)},
            status=status.HTTP_201_CREATED,
        )
