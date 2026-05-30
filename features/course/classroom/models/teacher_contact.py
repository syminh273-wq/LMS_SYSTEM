from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class TeacherContact(DjangoCassandraModel):
    """
    One row per (teacher, student) pair — written once when a student is
    approved into any of the teacher's classrooms.  Never duplicated.
    Query: "all students who ever studied with teacher X"
    """
    teacher_id    = columns.UUID(partition_key=True)
    consumer_uid  = columns.UUID(primary_key=True, clustering_order="ASC")

    consumer_name   = columns.Text(default='')
    first_name      = columns.Text(default='')
    last_name       = columns.Text(default='')
    consumer_email  = columns.Text(default='')
    consumer_avatar = columns.Text(default='')
    first_joined_at = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'course_teacher_contacts'

    class Meta:
        get_pk_field = 'consumer_uid'
