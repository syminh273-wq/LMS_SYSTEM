from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from features.account.space.models import Space
from features.course.exam.serializers import (
    ExamSubmissionRequestSerializer,
    serialize_exam_submission,
)
from features.course.exam.services import ExamSubmissionService
from features.course.grade.serializers import TeacherGradeRequestSerializer
from features.course.grade.services import GradeService


def exam_submission_error_response(exc):
    message = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST

    if message in {"Exam not found", "Resource not found", "Submission not found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif message in {
        "Student is not a member of this classroom",
        "Resource does not belong to this student",
    }:
        status_code = status.HTTP_403_FORBIDDEN

    return Response({"error": message}, status=status_code)


class ConsumerExamSubmissionViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def post(self, request, exam_uid):
        serializer = ExamSubmissionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            submission, created = self.submission_service.submit_exam(
                exam_id=exam_uid,
                student_id=request.user.uid,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return exam_submission_error_response(exc)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serialize_exam_submission(submission), status=response_status)


class ConsumerMyExamSubmissionViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def get(self, request, exam_uid):
        try:
            submission = self.submission_service.get_my_submission(
                exam_id=exam_uid,
                student_id=request.user.uid,
            )
        except ValueError as exc:
            if str(exc) == "Submission not found":
                return Response(None, status=status.HTTP_200_OK)
            return exam_submission_error_response(exc)

        return Response(serialize_exam_submission(submission))


class SpaceExamSubmissionViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def get(self, request, exam_uid):
        submissions = self.submission_service.list_exam_submissions(
            exam_id=exam_uid,
            teacher_id=request.user.uid,
        )
        return Response([serialize_exam_submission(submission) for submission in submissions])


class SpaceExamSubmissionDetailViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def get(self, request, submission_uid):
        submission = self.submission_service.get_teacher_submission(
            submission_id=submission_uid,
            teacher_id=request.user.uid,
        )
        return Response(serialize_exam_submission(submission))


class SpaceExamSubmissionGradeViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grade_service = GradeService()

    def patch(self, request, submission_uid):
        if not isinstance(request.user, Space):
            return Response(
                {"error": "Only teachers can grade submissions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TeacherGradeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            _, submission = self.grade_service.teacher_grade_submission(
                submission_id=submission_uid,
                teacher_id=request.user.uid,
                data=serializer.validated_data,
            )
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return exam_submission_error_response(exc)
        return Response(serialize_exam_submission(submission))
