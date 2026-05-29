import json
import logging
from datetime import datetime

from features.course.exam.models.exam_audit_log import ExamAuditLog

logger = logging.getLogger(__name__)


class ExamAuditLogRepository:

    def log(self, exam_id, student_id, event_type: str, event_data: dict | None = None):
        try:
            ExamAuditLog.create(
                exam_id=exam_id,
                student_id=student_id,
                event_type=event_type,
                event_data=json.dumps(event_data or {}, default=str),
                created_at=datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning(f"ExamAuditLog.log failed: {exc}")

    def list_by_exam(self, exam_id) -> list:
        return list(ExamAuditLog.objects.filter(exam_id=exam_id))

    def list_by_student(self, exam_id, student_id) -> list:
        return list(
            ExamAuditLog.objects.filter(exam_id=exam_id, student_id=student_id).allow_filtering()
        )
