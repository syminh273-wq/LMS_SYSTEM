from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from features.course.exam.serializers import (
    ExamSubmissionAIGradeSerializer,
    ExamSubmissionGradeSerializer,
    ExamSubmissionRequestSerializer,
    serialize_exam_submission,
)
from features.course.exam.services import ExamSubmissionService


def exam_submission_error_response(exc):
    message = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST

    if message in {"Exam not found", "Resource not found"}:
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def patch(self, request, submission_uid):
        serializer = ExamSubmissionGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission = self.submission_service.grade_submission(
            submission_id=submission_uid,
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(serialize_exam_submission(submission))


class SpaceExamSubmissionAIGradeViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def post(self, request, submission_uid):
        serializer = ExamSubmissionAIGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            submission = self.submission_service.ai_grade_submission(
                submission_id=submission_uid,
                teacher_id=request.user.uid,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return exam_submission_error_response(exc)

        return Response(serialize_exam_submission(submission))


class SpaceExamSubmissionsAIGradeViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def post(self, request, exam_uid):
        serializer = ExamSubmissionAIGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            results = self.submission_service.ai_grade_exam_submissions(
                exam_id=exam_uid,
                teacher_id=request.user.uid,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return exam_submission_error_response(exc)

        return Response(serialize_ai_grade_batch(results))


class SpaceClassroomExamSubmissionsAIGradeViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def post(self, request, classroom_uid):
        serializer = ExamSubmissionAIGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = self.submission_service.ai_grade_classroom_submissions(
            classroom_id=classroom_uid,
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(serialize_ai_grade_batch(results))


def serialize_ai_grade_batch(results):
    graded = [result for result in results if result["success"]]
    failed = [result for result in results if not result["success"]]
    return {
        "total": len(results),
        "graded": len(graded),
        "failed": len(failed),
        "results": [
            {
                "success": result["success"],
                "error": result["error"],
                "submission": serialize_exam_submission(result["submission"]),
            }
            for result in results
        ],
    }
