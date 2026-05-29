from datetime import datetime

from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class ExamAuditLog(DjangoCassandraModel):
    """
    Audit trail for exam lifecycle events per student.
    Partition key = exam_id so teachers can query all events for an exam efficiently.
    event_type: joined | submitted | timeout_submit | face_warning | face_scan
    """
    exam_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    student_id = columns.UUID(index=True, required=True)
    event_type = columns.Text(required=True)
    event_data = columns.Text(default='{}')
    created_at = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'exam_audit_logs'

    class Meta:
        get_pk_field = 'uid'
