from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.face.services import FaceRecognitionService


class SpaceFaceViewSet(ViewSet):
    """
    Teacher/admin endpoints to view face verification logs.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FaceRecognitionService()

    def exam_logs(self, request, exam_uid=None):
        """
        GET /api/v1/space/face/exams/<exam_uid>/logs/
        Returns all verification events for an exam (sorted newest-first by Cassandra).
        """
        logs = self.service.get_exam_logs(exam_id=exam_uid)
        data = [
            {
                "uid": str(log.uid),
                "student_id": str(log.student_id),
                "camera_open": log.camera_open,
                "recognized": log.recognized,
                "multiple_faces": log.multiple_faces,
                "face_count": log.face_count,
                "similarity": log.similarity,
                "verified_at": log.verified_at.isoformat() if log.verified_at else None,
            }
            for log in logs
        ]
        return Response(data)
