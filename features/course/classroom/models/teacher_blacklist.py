from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


GLOBAL_SENTINEL = '00000000-0000-0000-0000-000000000000'


class TeacherBlacklist(BaseTimeStampModel):
    """
    Unified blacklist — replaces `course_classroom_blacklists` and
    `course_teacher_global_blacklists`.

    Partition = teacher_id  →  O(1) lookup cho mọi query theo teacher.
    Clustering = (classroom_uid ASC, consumer_uid DESC)  →  truy vấn
    theo (teacher, classroom) hoặc (teacher, global) đều nhanh.

    Scope convention:
      - classroom_uid == GLOBAL_SENTINEL (uuid zero)  →  teacher-wide block
      - classroom_uid == <real uuid>                  →  per-classroom block
    """

    teacher_id    = columns.UUID(partition_key=True, primary_key=True, required=True)
    classroom_uid = columns.UUID(primary_key=True, default=GLOBAL_SENTINEL, required=True)
    consumer_uid  = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC", required=True)

    reason   = columns.Text(default='')
    added_by = columns.UUID(required=False)

    __table_name__ = 'course_blacklists'

    class Meta:
        get_pk_field = 'consumer_uid'
