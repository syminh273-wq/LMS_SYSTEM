from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.quiz_collection.serializers.quiz_collection_response_serializer import (
    QuizCollectionResponseSerializer,
    QuizCollectionDetailResponseSerializer,
    QuizCollectionProgressResponseSerializer,
)
from features.quiz_collection.serializers.issued_certificate_response_serializer import (
    IssuedCertificateResponseSerializer,
)
from features.quiz_collection.services import (
    QuizCollectionService,
    CertificateIssuanceService,
)
from features.quiz_collection.repositories import IssuedCertificateRepository


class ConsumerQuizCollectionViewSet(ViewSet):
    service = QuizCollectionService()
    issuance_service = CertificateIssuanceService()
    issued_repo = IssuedCertificateRepository()

    def list(self, request):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        collections = self.service.get_for_classroom(classroom_id)
        return Response(QuizCollectionResponseSerializer(collections, many=True).data)

    def retrieve(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        if not self.service.assignment_repo.find_assignment(pk, classroom_id):
            raise NotFound('Collection not assigned to this classroom.')
        data = self.service.get_detail(pk)
        return Response(QuizCollectionDetailResponseSerializer({
            **{f: getattr(data['collection'], f) for f in [
                'uid', 'created_by', 'title', 'description', 'quiz_count',
                'certificate_id', 'status', 'created_at', 'updated_at',
            ]},
            'items': data['items'],
            'assignments': data['assignments'],
        }).data)

    @action(detail=True, methods=['get'], url_path='progress')
    def progress(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        if not self.service.assignment_repo.find_assignment(pk, classroom_id):
            raise NotFound('Collection not assigned to this classroom.')
        progress = self.issuance_service.get_student_progress(pk, classroom_id, request.user.uid)
        return Response(QuizCollectionProgressResponseSerializer(progress).data)

    @action(detail=True, methods=['get'], url_path='certificate')
    def certificate(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        if not self.service.assignment_repo.find_assignment(pk, classroom_id):
            raise NotFound('Collection not assigned to this classroom.')
        issued = self.issued_repo.find_for_collection_classroom_student(
            pk, classroom_id, request.user.uid
        )
        if not issued:
            raise NotFound('No certificate has been issued yet.')
        return Response(IssuedCertificateResponseSerializer(issued).data)

    @action(detail=False, methods=['get'], url_path='my-certificates')
    def my_certificates(self, request):
        certs = self.issued_repo.get_by_student(request.user.uid)
        return Response(IssuedCertificateResponseSerializer(certs, many=True).data)
