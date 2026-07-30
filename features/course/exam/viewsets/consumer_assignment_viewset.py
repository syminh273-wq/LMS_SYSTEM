from rest_framework import status
from rest_framework.response import Response

from features.course.exam.viewsets.consumer_exam_viewset import ConsumerExamViewSet, _serialize_exam


class ConsumerAssignmentViewSet(ConsumerExamViewSet):
    """Dedicated student-facing endpoint for 'bài tập' (exam_type=assignment),
    separate from /exams/ which is now scoped to 'bài kiểm tra' (exam_type=quiz)."""

    def list_classroom_assignments(self, request, uid=None):
        exams = self.exam_service.list_student_exams(uid, exam_type="assignment")
        return Response([_serialize_exam(e) for e in exams])

    def submit(self, request, exam_uid=None):
        try:
            exam = self.exam_service.get_exam(exam_uid)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if getattr(exam, "exam_type", "assignment") != "assignment":
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
        return super().submit(request, exam_uid=exam_uid)
