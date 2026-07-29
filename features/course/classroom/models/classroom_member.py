from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class ClassroomMember(DjangoCassandraModel):
    classroom_uid = columns.UUID(partition_key=True)
    member_id = columns.UUID(primary_key=True, clustering_order="ASC")
    member_type = columns.Text(default='consumer')   # 'space' | 'consumer'
    member_name = columns.Text(default='')
    member_avatar = columns.Text(default='')
    role = columns.Text(default='student')            # 'teacher' | 'student'
    joined_at = columns.DateTime(default=datetime.utcnow)
    status = columns.Text(default='approved')          # 'pending' | 'approved'
    is_deleted = columns.Boolean(default=False)
    is_verified = columns.Boolean(default=False)
    verified_at = columns.DateTime(required=False)
    has_paid = columns.Boolean(default=False, index=True)
    paid_at = columns.DateTime(required=False)

    __table_name__ = 'course_classroom_members'

    class Meta:
        get_pk_field = 'member_id'
