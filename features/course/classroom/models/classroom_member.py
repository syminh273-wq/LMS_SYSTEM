from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class ClassroomMember(DjangoCassandraModel):
    member_id = columns.UUID(partition_key=True)
    classroom_uid = columns.UUID(primary_key=True, clustering_order="DESC", index=True)
    member_type = columns.Text(default='consumer')   # 'space' | 'consumer'
    member_name = columns.Text(default='')
    member_avatar = columns.Text(default='')
    role = columns.Text(default='student')            # 'teacher' | 'student'
    joined_at = columns.DateTime(default=datetime.utcnow)
    is_deleted = columns.Boolean(default=False)

    __table_name__ = 'course_classroom_members'

    class Meta:
        get_pk_field = 'classroom_uid'
