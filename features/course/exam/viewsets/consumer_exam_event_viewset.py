import json as _json
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.course.exam.services import ExamAuditEventService

logger = logging.getLogger(__name__)


class ConsumerExamEventViewSet(ViewSet):
    """
    Endpoint used by the student exam-session page to record proctoring events:

      POST /api/v1/consumer/course/exam-sessions/<session_uid>/events/
      body: { event_type, event_data? }

    Returns:
      { logged, warning, count, max, remaining, force_submitted, submission }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ExamAuditEventService()

    def record_event(self, request, session_uid=None):
        event_type = request.data.get("event_type")
        event_data = request.data.get("event_data") or {}
        if not isinstance(event_data, dict):
            try:
                event_data = _json.loads(event_data)
            except Exception:
                event_data = {}

        try:
            result = self.service.record_event(
                session_uid=session_uid,
                student_id=request.user.uid,
                event_type=event_type,
                event_data=event_data,
            )
            return Response(result)
        except ValueError as exc:
            message = str(exc)
            code = status.HTTP_400_BAD_REQUEST
            if "not found" in message.lower():
                code = status.HTTP_404_NOT_FOUND
            elif "belong" in message.lower() or "active" in message.lower():
                code = status.HTTP_403_FORBIDDEN
            return Response({"error": message, "logged": False}, status=code)
        except Exception as exc:
            logger.exception(f"ConsumerExamEventViewSet.record_event error: {exc}")
            return Response(
                {"error": "Internal error", "logged": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
