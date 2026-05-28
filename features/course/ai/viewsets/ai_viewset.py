from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import UserScopeMixin
from features.course.ai.serializers.ai_serializer import (
    AIAskSerializer,
    AIIngestSerializer,
    AIQueryParamSerializer,
)
from features.course.ai.services.course_ai_service import CourseAIService


class CourseAIViewSet(UserScopeMixin, ViewSet):
    """
    AI/RAG endpoints for teachers (space users).

    All endpoints require JWT auth and at least one of:
      ?classroom_id=<uuid>   filter by classroom (teacher must own it)
      ?document_id=<uuid>    filter by document  (teacher must own it)

    POST  ai/ask/     — ask a question, get AI answer from course documents
    POST  ai/ingest/  — index a resource file into the vector store
    DELETE ai/index/  — remove indexed chunks for a classroom / document
    """

    def _parse_query_params(self, request):
        qs = AIQueryParamSerializer(data=request.query_params)
        qs.is_valid(raise_exception=True)
        return qs.validated_data

    # ── POST ai/ask/ ─────────────────────────────────────────────────────────

    @action(detail=False, methods=["post"], url_path="ask")
    def ask(self, request):
        params = self._parse_query_params(request)

        body = AIAskSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        result = CourseAIService.ask(
            teacher_id=request.user.uid,
            question=body.validated_data["question"],
            classroom_id=params.get("classroom_id"),
            document_id=params.get("document_id"),
            top_k=body.validated_data["top_k"],
        )
        return Response(result, status=status.HTTP_200_OK)

    # ── POST ai/ingest/ ──────────────────────────────────────────────────────

    @action(detail=False, methods=["post"], url_path="ingest")
    def ingest(self, request):
        params = self._parse_query_params(request)

        body = AIIngestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        result = CourseAIService.ingest(
            teacher_id=request.user.uid,
            resource_id=body.validated_data["resource_id"],
            classroom_id=params.get("classroom_id"),
            document_id=params.get("document_id"),
        )

        code = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=code)

    # ── DELETE ai/index/ ─────────────────────────────────────────────────────

    @action(detail=False, methods=["delete"], url_path="index")
    def delete_index(self, request):
        params = self._parse_query_params(request)

        result = CourseAIService.delete_index(
            teacher_id=request.user.uid,
            classroom_id=params.get("classroom_id"),
            document_id=params.get("document_id"),
        )
        return Response(result, status=status.HTTP_200_OK)
