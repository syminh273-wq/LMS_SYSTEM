from datetime import datetime

from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class DocReadingProgress(BaseTimeStampModel):
    classroom_id = columns.UUID(partition_key=True)
    student_id = columns.UUID(primary_key=True, clustering_order="DESC")
    resource_uid = columns.UUID(primary_key=True, clustering_order="DESC")

    read_progress = columns.Integer(default=0)
    is_completed = columns.Boolean(default=False)
    completed_at = columns.DateTime(required=False)
    last_opened_at = columns.DateTime(default=datetime.now)

    class Meta:
        get_pk_field = 'resource_uid'

    __table_name__ = 'resource_doc_reading_progress'
