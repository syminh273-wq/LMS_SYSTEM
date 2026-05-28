from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from features.account.space.models import Space
from features.course.grade.serializers import (
    AIGradeRequestSerializer,
    TeacherGradeRequestSerializer,
    serialize_grade,
)
from features.course.grade.services import GradeService


def grade_error_response(exc):
    if isinstance(exc, PermissionError):
        return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    if str(exc) in {"Submission not found", "Exam not found", "AI grade suggestion not found"}:
        return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, RuntimeError):
        return Response({"error": "AI grading service is unavailable"}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class SpaceGradeViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def require_teacher(self, request):
        if not isinstance(request.user, Space):
            return Response(
                {"error": "Only teachers can grade submissions"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None


class SpaceAIGradeViewSet(SpaceGradeViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grade_service = GradeService()

    def post(self, request, submission_uid):
        denied = self.require_teacher(request)
        if denied:
            return denied

        serializer = AIGradeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            grade = self.grade_service.ai_grade_submission(
                submission_uid,
                request.user.uid,
                serializer.validated_data,
            )
        except (ValueError, PermissionError, RuntimeError) as exc:
            return grade_error_response(exc)
        return Response(serialize_grade(grade), status=status.HTTP_201_CREATED)


class SpaceTeacherGradeViewSet(SpaceGradeViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grade_service = GradeService()

    def patch(self, request, submission_uid):
        denied = self.require_teacher(request)
        if denied:
            return denied

        serializer = TeacherGradeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            grade, _ = self.grade_service.teacher_grade_submission(
                submission_uid,
                request.user.uid,
                serializer.validated_data,
            )
        except (ValueError, PermissionError) as exc:
            return grade_error_response(exc)
        return Response(serialize_grade(grade))


class SpaceSubmissionGradeHistoryViewSet(SpaceGradeViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grade_service = GradeService()

    def get(self, request, submission_uid):
        denied = self.require_teacher(request)
        if denied:
            return denied

        try:
            grades = self.grade_service.list_submission_grades(
                submission_uid,
                request.user.uid,
            )
        except (ValueError, PermissionError) as exc:
            return grade_error_response(exc)
        return Response([serialize_grade(grade) for grade in grades])
