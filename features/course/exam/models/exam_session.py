from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class ExamSession(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)

    uid = columns.UUID(
        primary_key=True,
        default=uuid7,
        clustering_order="DESC"
    )

    exam_id = columns.UUID(index=True, required=True)
    student_id = columns.UUID(index=True, required=True)
    token = columns.Text(index=True, required=False)
    token_status = columns.Text(default='pending')  # 'pending' | 'active' | 'expired' | 'completed'
    token_expires_at = columns.DateTime(required=False)  # pending TTL
    started_at = columns.DateTime(required=False)
    ends_at = columns.DateTime(required=False)

    # Anti-cheat counters (gộp tab + window + fullscreen + visibility vào 1 counter)
    visibility_breaks_count = columns.Integer(default=0)
    face_warnings_count = columns.Integer(default=0)
    last_event_at = columns.DateTime(required=False)

    __table_name__ = 'course_exam_sessions'

    class Meta:
        get_pk_field = 'uid'
