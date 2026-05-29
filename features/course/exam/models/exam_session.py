from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class ExamSession(DjangoCassandraModel):
    exam_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    student_id = columns.UUID(index=True, required=True)
    token = columns.Text(index=True, default='')
    token_status = columns.Text(default='pending')  # 'pending' | 'active' | 'expired' | 'completed'
    token_expires_at = columns.DateTime(required=False)  # pending TTL
    started_at = columns.DateTime(required=False)
    ends_at = columns.DateTime(required=False)

    __table_name__ = 'exam_sessions'

    class Meta:
        get_pk_field = 'uid'
