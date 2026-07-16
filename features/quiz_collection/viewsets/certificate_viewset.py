from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.quiz_collection.serializers.certificate_request_serializer import (
    CertificateCreateRequestSerializer,
    CertificateUpdateRequestSerializer,
)
from features.quiz_collection.serializers.certificate_response_serializer import (
    CertificateResponseSerializer,
)
from features.quiz_collection.services import CertificateService


class CertificateViewSet(ViewSet):
    service = CertificateService()

    def list(self, request):
        certs = list(self.service.get_by_teacher(request.user.uid))
        return Response(CertificateResponseSerializer(certs, many=True).data)

    def retrieve(self, request, pk=None):
        cert = self.service.find(pk)
        if str(cert.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to view this certificate.')
        return Response(CertificateResponseSerializer(cert).data)

    def create(self, request):
        serializer = CertificateCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        cert = self.service.create(
            created_by=request.user.uid,
            name=d['name'],
            description=d.get('description', ''),
            template_url=d.get('template_url'),
            template_image=request.FILES.get('template_image'),
        )
        return Response(
            CertificateResponseSerializer(cert).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        cert = self.service.find(pk)
        if str(cert.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to update this certificate.')
        serializer = CertificateUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if 'template_url' in data and data['template_url'] == '':
            data['template_url'] = None
        updated = self.service.update(
            cert,
            template_image=request.FILES.get('template_image'),
            **data,
        )
        return Response(CertificateResponseSerializer(updated).data)

    def destroy(self, request, pk=None):
        cert = self.service.find(pk)
        if str(cert.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to delete this certificate.')
        self.service.delete(cert)
        return Response(status=status.HTTP_204_NO_CONTENT)
