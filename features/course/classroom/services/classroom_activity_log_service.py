import json
import uuid
from datetime import datetime

from features.course.classroom.models.classroom_activity_log import ClassroomActivityLog


class ClassroomActivityLogService:
    """
    Write and read classroom activity logs.

    Usage (fire-and-forget; never raise to callers):
        ClassroomActivityLogService().log(
            classroom_uid=classroom.uid,
            log_level='major',
            event_type='exam_opened',
            actor_id=request.user.uid,
            actor_name=request.user.full_name,
            actor_role='teacher',
            target_id=exam.uid,
            target_name=exam.title,
        )
    """

    # ── Write ─────────────────────────────────────────────────────────────────

    def log(
        self,
        classroom_uid,
        log_level: str,
        event_type: str,
        actor_id,
        actor_name: str = '',
        actor_role: str = '',
        target_id=None,
        target_name: str = '',
        metadata: dict | None = None,
    ):
        try:
            ClassroomActivityLog.create(
                classroom_uid=uuid.UUID(str(classroom_uid)),
                log_level=log_level,
                event_type=event_type,
                actor_id=uuid.UUID(str(actor_id)),
                actor_name=actor_name or '',
                actor_role=actor_role or '',
                target_id=uuid.UUID(str(target_id)) if target_id else None,
                target_name=target_name or '',
                metadata=json.dumps(metadata or {}),
                created_at=datetime.utcnow(),
            )
        except Exception:
            pass  # logging must never crash the main request

    # ── Read ──────────────────────────────────────────────────────────────────

    def list(
        self,
        classroom_uid,
        log_level: str | None = None,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[dict]:
        """
        Return activity logs for a classroom, newest first.
        Filter by log_level at Python level (Cassandra partition is classroom_uid).
        """
        try:
            qs = ClassroomActivityLog.objects.filter(
                classroom_uid=uuid.UUID(str(classroom_uid))
            ).order_by('-created_at')

            if before:
                qs = qs.filter(created_at__lt=before)

            rows = list(qs.limit(limit * 3 if log_level else limit))

            if log_level:
                rows = [r for r in rows if r.log_level == log_level][:limit]
            else:
                rows = rows[:limit]

            return [self._serialize(r) for r in rows]
        except Exception:
            return []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize(row: ClassroomActivityLog) -> dict:
        return {
            'uid': str(row.uid),
            'log_level': row.log_level,
            'event_type': row.event_type,
            'actor_id': str(row.actor_id),
            'actor_name': row.actor_name,
            'actor_role': row.actor_role,
            'target_id': str(row.target_id) if row.target_id else None,
            'target_name': row.target_name,
            'metadata': json.loads(row.metadata or '{}'),
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }
