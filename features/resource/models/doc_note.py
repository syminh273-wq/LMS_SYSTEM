from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class DocNote(BaseTimeStampModel):
    resource_uid = columns.UUID(partition_key=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    classroom_id = columns.UUID(index=True)
    student_id = columns.UUID(index=True)
    content = columns.Text(required=True)
    page = columns.Integer(required=False)
    x_pct = columns.Float(required=False)
    y_pct = columns.Float(required=False)
    progress_at = columns.Float(default=0.0)
    color = columns.Text(default='yellow')

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'resource_doc_notes'
