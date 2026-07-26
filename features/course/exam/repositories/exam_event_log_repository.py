import json
import logging
from datetime import datetime

from features.course.exam.models.exam_event_log import ExamEventLog

logger = logging.getLogger(__name__)


class ExamEventLogRepository:
    """
    Repository for the unified `exam_event_logs` table.

    Replaces the old ExamAuditLogRepository and the face-verification
    log writes/reads previously in FaceRecognitionService.

    All structured per-event payload (face telemetry, audit extras, …)
    is serialized as JSON into `event_data`. The model has no per-field
    columns beyond event_kind / event_type, so adding new event
    attributes never requires an `ALTER TABLE`.

    Backward-compat shim:
      - `log(...)` keeps the old call site signature (audit write).
      - `list_by_student(...)` returns audit rows for a student.
      - `get_face_logs_for_exam/student(...)` return face rows.
    """

    EVENT_KIND_AUDIT = 'audit'
    EVENT_KIND_FACE = 'face'

    # ── audit writes ──────────────────────────────────────────────────────────

    def log(self, exam_id, student_id, event_type: str, event_data: dict | None = None):
        try:
            ExamEventLog.create(
                exam_id=exam_id,
                student_id=student_id,
                event_kind=self.EVENT_KIND_AUDIT,
                event_type=event_type,
                event_data=json.dumps(event_data or {}, default=str),
                created_at=datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning(f"ExamEventLog.log failed: {exc}")

    # Backward-compat alias used by exam_submission_service / new code.
    def log_audit(self, exam_id, student_id, event_type: str, event_data: dict | None = None):
        return self.log(exam_id, student_id, event_type, event_data)

    # ── face writes ───────────────────────────────────────────────────────────

    def log_face(self, exam_id, student_id, result: dict, verified_at=None):
        try:
            payload = dict(result or {})
            payload.setdefault('verified_at', (verified_at or datetime.utcnow()).isoformat())
            ExamEventLog.create(
                exam_id=exam_id,
                student_id=student_id,
                event_kind=self.EVENT_KIND_FACE,
                event_type='face_verify',
                event_data=json.dumps(payload, default=str),
                created_at=datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning(f"ExamEventLog.log_face failed: {exc}")

    # ── reads (audit) ─────────────────────────────────────────────────────────

    def list_by_exam(self, exam_id) -> list:
        return list(
            ExamEventLog.objects.filter(
                exam_id=exam_id, event_kind=self.EVENT_KIND_AUDIT
            ).allow_filtering()
        )

    def list_by_student(self, exam_id, student_id) -> list:
        return list(
            ExamEventLog.objects.filter(
                exam_id=exam_id,
                student_id=student_id,
                event_kind=self.EVENT_KIND_AUDIT,
            ).allow_filtering()
        )

    # ── reads (face) ──────────────────────────────────────────────────────────

    def get_face_logs_for_exam(self, exam_id) -> list:
        return list(
            ExamEventLog.objects.filter(
                exam_id=exam_id, event_kind=self.EVENT_KIND_FACE
            ).allow_filtering()
        )

    def get_face_logs_for_student(self, exam_id, student_id) -> list:
        return list(
            ExamEventLog.objects.filter(
                exam_id=exam_id,
                student_id=student_id,
                event_kind=self.EVENT_KIND_FACE,
            ).allow_filtering()
        )

    # ── helpers used by serializers / views ───────────────────────────────────

    @staticmethod
    def parse_event_data(row) -> dict:
        try:
            return json.loads(row.event_data or '{}')
        except Exception:
            return {}
