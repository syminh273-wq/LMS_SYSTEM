from django.http import QueryDict
from rest_framework import status
from rest_framework.response import Response

from features.course.exam.viewsets.space_exam_viewset import SpaceExamViewSet, _serialize_exam
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService


def _to_plain_dict(data):
    """QueryDict stores values as lists internally; **data unpacking bypasses
    its __getitem__ override and leaks those raw lists (e.g. classroom_id
    becomes ['<uuid>']). QueryDict.dict() collapses each key to its last
    scalar value, which is what downstream **data unpacking needs."""
    if isinstance(data, QueryDict):
        return data.dict()
    return dict(data) if not isinstance(data, dict) else data.copy()


class SpaceAssignmentViewSet(SpaceExamViewSet):
    """Dedicated endpoint for 'bài tập' (exam_type=assignment). Reuses the Exam
    model/service layer but exposes its own URL surface, separate from /exams/
    which is now scoped to 'bài kiểm tra' (exam_type=quiz)."""

    def list(self, request):
        classroom_id = request.query_params.get("classroom_id")
        req_status = request.query_params.getlist("status") or request.query_params.get("status") or None
        exams = self.exam_service.list_teacher_exams(
            teacher_id=request.user.uid,
            classroom_id=classroom_id,
            status=req_status,
            exam_type="assignment",
        )
        return Response([_serialize_exam(e) for e in exams])

    def retrieve(self, request, uid=None):
        exam = self.exam_service.get_exam(uid)
        if getattr(exam, "exam_type", "assignment") != "assignment":
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_exam(exam))

    def create(self, request):
        data = _to_plain_dict(request.data)
        data["exam_type"] = "assignment"
        file_obj = request.FILES.get('file')

        try:
            exam = self.exam_service.create_exam(request.user.uid, data, file_obj=file_obj)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        ClassroomActivityLogService().log(
            classroom_uid=exam.classroom_id,
            log_level='major',
            event_type='exam_created',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=exam.uid,
            target_name=exam.title,
        )
        return Response(_serialize_exam(exam), status=status.HTTP_201_CREATED)

    def update(self, request, uid=None):
        try:
            exam = self.exam_service.get_exam(uid)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if getattr(exam, "exam_type", "assignment") != "assignment":
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

        data = _to_plain_dict(request.data)
        data["exam_type"] = "assignment"
        file_obj = request.FILES.get('file')
        prev_status = exam.status
        updated = self.exam_service.update_exam(uid, data, file_obj=file_obj)

        if data.get('status') == 'published' and prev_status != 'published':
            ClassroomActivityLogService().log(
                classroom_uid=updated.classroom_id,
                log_level='major',
                event_type='exam_published',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=updated.uid,
                target_name=updated.title,
            )
        return Response(_serialize_exam(updated))

    def destroy(self, request, uid=None):
        try:
            exam = self.exam_service.get_exam(uid)
        except ValueError:
            exam = None
        if exam is not None and getattr(exam, "exam_type", "assignment") != "assignment":
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
        return super().destroy(request, uid=uid)
