import json

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import SpaceScopeMixin
from features.face.services import FaceRecognitionService
from features.course.exam.repositories.exam_event_log_repository import ExamEventLogRepository


def _serialize_log(log) -> dict:
    data = ExamEventLogRepository.parse_event_data(log)
    return {
        "uid": str(log.uid),
        "student_id": str(log.student_id),
        "camera_open": data.get("camera_open", False),
        "recognized": data.get("recognized", False),
        "multiple_faces": data.get("multiple_faces", False),
        "face_count": data.get("face_count", 0),
        "similarity": data.get("similarity", 0.0),
        "verified_at": data.get("verified_at"),
    }


class SpaceFaceViewSet(SpaceScopeMixin, ViewSet):
    """
    Teacher/admin endpoints to view face verification logs.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FaceRecognitionService()

    def exam_logs(self, request, exam_uid=None):
        """
        List all face-verification events for an exam.
        @return: verification events
        """
        logs = self.service.get_exam_logs(exam_id=exam_uid)
        return Response([_serialize_log(log) for log in logs])

    def student_logs(self, request, exam_uid=None, student_uid=None):
        """
        List face-verification events for a single student in an exam.
        @return: verification events
        """
        logs = self.service.get_student_exam_logs(
            exam_id=exam_uid, student_id=student_uid
        )
        return Response([_serialize_log(log) for log in logs])
