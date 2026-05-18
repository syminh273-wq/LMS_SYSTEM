from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from features.course.exam.serializers import (
    ExamSubmissionGradeSerializer,
    ExamSubmissionRequestSerializer,
    serialize_exam_submission,
)
from features.course.exam.services import ExamSubmissionService


class ConsumerExamSubmissionViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def post(self, request, exam_uid):
        serializer = ExamSubmissionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission, created = self.submission_service.submit_exam(
            exam_id=exam_uid,
            student_id=request.user.uid,
            data=serializer.validated_data,
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serialize_exam_submission(submission), status=response_status)


class ConsumerMyExamSubmissionViewSet(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submission_service = ExamSubmissionService()

    def get(self, request, exam_uid):
        submission = self.submission_service.get_my_submission(
            exam_id=exam_uid,
            student_id=request.user.uid,
        )
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
