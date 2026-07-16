from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.quiz_collection.serializers.quiz_collection_request_serializer import (
    QuizCollectionCreateRequestSerializer,
    QuizCollectionUpdateRequestSerializer,
    QuizCollectionAddItemsRequestSerializer,
    QuizCollectionReorderRequestSerializer,
    QuizCollectionAssignRequestSerializer,
)
from features.quiz_collection.serializers.quiz_collection_response_serializer import (
    QuizCollectionResponseSerializer,
    QuizCollectionDetailResponseSerializer,
    QuizCollectionAssignmentResponseSerializer,
)
from features.quiz_collection.services import QuizCollectionService
from features.quiz.repositories.quiz_repository import QuizRepository


class QuizCollectionViewSet(ViewSet):
    service = QuizCollectionService()
    quiz_service = QuizRepository()

    def list(self, request):
        collections = list(self.service.get_by_teacher(request.user.uid))
        return Response(QuizCollectionResponseSerializer(collections, many=True).data)

    def retrieve(self, request, pk=None):
        data = self.service.get_detail(pk)
        if str(data['collection'].created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to view this collection.')
        return Response(QuizCollectionDetailResponseSerializer({
            **{f: getattr(data['collection'], f) for f in [
                'uid', 'created_by', 'title', 'description', 'quiz_count',
                'certificate_id', 'status', 'created_at', 'updated_at',
            ]},
            'items': data['items'],
            'assignments': data['assignments'],
        }).data)

    def create(self, request):
        serializer = QuizCollectionCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        collection = self.service.create(
            created_by=request.user.uid,
            title=d['title'],
            description=d.get('description', ''),
            certificate_id=d.get('certificate_id'),
        )
        return Response(
            QuizCollectionResponseSerializer(collection).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to update this collection.')
        serializer = QuizCollectionUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = self.service.update(collection, **serializer.validated_data)
        return Response(QuizCollectionResponseSerializer(updated).data)

    def destroy(self, request, pk=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to delete this collection.')
        self.service.delete(collection)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='items')
    def add_items(self, request, pk=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to modify this collection.')
        serializer = QuizCollectionAddItemsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        added = self.service.add_quizzes(pk, [str(q) for q in serializer.validated_data['quiz_ids']])
        return Response({'added': added}, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'items/(?P<quiz_id>[^/.]+)',
    )
    def remove_item(self, request, pk=None, quiz_id=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to modify this collection.')
        self.service.remove_quiz(pk, quiz_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path='reorder')
    def reorder(self, request, pk=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to modify this collection.')
        serializer = QuizCollectionReorderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ordered = [str(q) for q in serializer.validated_data['ordered_quiz_ids']]
        existing = set(self.service.item_repo.get_quiz_ids(pk))
        if set(ordered) != existing:
            return Response(
                {'detail': 'ordered_quiz_ids must contain exactly the same quiz_ids as the collection.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.service.reorder(pk, ordered)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to assign this collection.')
        serializer = QuizCollectionAssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from features.course.classroom.models import Classroom
        try:
            classroom = Classroom.objects.get(
                uid=serializer.validated_data['classroom_id'],
                is_deleted=False,
            )
        except Classroom.DoesNotExist:
            return Response({'detail': 'Classroom not found.'}, status=status.HTTP_404_NOT_FOUND)
        if str(classroom.teacher_id) != str(request.user.uid):
            raise PermissionDenied('You do not own this classroom.')
        self.service.assign_to_classroom(pk, serializer.validated_data['classroom_id'], request.user.uid)
        return Response(status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'assign/(?P<classroom_id>[^/.]+)',
    )
    def unassign(self, request, pk=None, classroom_id=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to unassign this collection.')
        self.service.unassign_from_classroom(pk, classroom_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='assignments')
    def assignments(self, request, pk=None):
        collection = self.service.find(pk)
        if str(collection.created_by) != str(request.user.uid):
            raise PermissionDenied('You do not have permission to view this collection.')
        assignments = self.service.assignment_repo.get_by_collection(pk)
        return Response(QuizCollectionAssignmentResponseSerializer(assignments, many=True).data)
