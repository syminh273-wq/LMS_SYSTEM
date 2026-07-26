from datetime import datetime

from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class ExamEventLog(DjangoCassandraModel):
    """
    Unified event log for one exam, replacing both `exam_audit_logs` and
    `face_verification_logs`. Partition by `exam_id` so all events for an
    exam (audit + face + visibility + lifecycle) are co-located.

    event_kind:
        audit    — lifecycle & visibility events (joined, submitted,
                   timeout_submit, force_submitted, tab_leave, ...)
        face     — per-frame face verification telemetry (camera_open,
                   recognized, similarity, ...)

    event_type carries the fine-grained event name. All per-event
    structured payload (including face telemetry like camera_open /
    recognized / multiple_faces / face_count / similarity / verified_at)
    is stored as JSON in `event_data` — the FE can read whichever keys
    it needs without the model having to grow a new column every time
    a new field is added.
    """
    exam_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    student_id = columns.UUID(index=True, required=True)
    event_kind = columns.Text(required=True)        # 'audit' | 'face'
    event_type = columns.Text(required=True)
    event_data = columns.Text(default='{}')

    created_at = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'exam_event_logs'

    class Meta:
        get_pk_field = 'uid'
