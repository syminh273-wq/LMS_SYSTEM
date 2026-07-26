from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class TeacherGlobalBlacklist(BaseTimeStampModel):
    """
    Teacher-wide block. Partition = teacher_id  →  fast
    "list all students this teacher has globally banned" and O(1)
    lookup by (teacher_id, consumer_uid).

    Distinct from ClassroomBlacklist so the partition is never mixed
    between scopes and queries can scan a single partition cleanly.
    """

    teacher_id   = columns.UUID(partition_key=True, primary_key=True, required=True)
    consumer_uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC", required=True)

    reason   = columns.Text(default='')
    added_by = columns.UUID(required=False)

    __table_name__ = 'course_teacher_global_blacklists'

    class Meta:
        get_pk_field = 'consumer_uid'
