from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import ConsumerScopeMixin
from features.face.services import FaceRecognitionService


class ConsumerFaceViewSet(ConsumerScopeMixin, ViewSet):
    """
    Student-facing endpoints for face enrollment and REST verification.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = FaceRecognitionService()

    def enroll(self, request):
        """
        Register (or re-register) the student's face.
        @param image: base64 jpeg/png
        @return: message, enrolled_at
        """
        image = request.data.get("image")
        if not image:
            return Response({"error": "image is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            record = self.service.enroll(
                student_id=request.user.uid,
                image_b64=image,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(
            {"message": "Face enrolled successfully", "enrolled_at": record.enrolled_at.isoformat()},
            status=status.HTTP_201_CREATED,
        )

    def verify(self, request, exam_uid=None):
        """
        One-shot face verification for an exam session (use WebSocket for continuous monitoring).
        @param image: base64 image
        @return: verification result
        """
        image = request.data.get("image")
        if not image:
            return Response({"error": "image is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = self.service.verify(
                student_id=request.user.uid,
                exam_id=exam_uid,
                image_b64=image,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result)

    def enrollment_status(self, request):
        """
        Check whether the student has an active face enrollment.
        @return: enrolled
        """
        embedding = self.service.get_active_embedding(request.user.uid)
        return Response({"enrolled": embedding is not None})

    def classroom_session_status(self, request, classroom_uid=None):
        """
        Get the current classroom face-session status (valid for 8 h).
        @return: session status
        """
        result = self.service.get_classroom_session(
            student_id=request.user.uid,
            classroom_uid=classroom_uid,
        )
        return Response(result)

    def verify_for_classroom(self, request, classroom_uid=None):
        """
        Verify identity for classroom entry; marks is_verified=True on success.
        @param image: base64 image
        @return: verification result
        """
        image = request.data.get("image")
        if not image:
            return Response({"error": "image is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = self.service.verify_for_classroom(
                student_id=request.user.uid,
                classroom_uid=classroom_uid,
                image_b64=image,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result)
