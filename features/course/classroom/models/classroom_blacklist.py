from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class ClassroomBlacklist(BaseTimeStampModel):
    # scope_id = teacher_id when scope='global', classroom_uid when scope='classroom'
    scope_id     = columns.UUID(partition_key=True)
    consumer_uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    scope        = columns.Text(index=True)   # 'global' | 'classroom'
    reason       = columns.Text(default='')
    added_by     = columns.UUID(required=False)

    __table_name__ = 'course_classroom_blacklist'

    class Meta:
        get_pk_field = 'consumer_uid'
