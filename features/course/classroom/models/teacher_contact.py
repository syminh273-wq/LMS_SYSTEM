from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class TeacherContact(DjangoCassandraModel):
    """
    One row per (teacher, student) pair — written when a student is
    approved into any of the teacher's classrooms.  Acts as a lightweight
    contact history: we keep the most recent interaction snapshot and a
    running contact_count so the teacher can quickly see who is still
    active vs. who was a one-off joiner.

    Query: "all students who ever studied with teacher X" — full partition
    scan is acceptable because partition size is bounded by the teacher's
    historical student count.

    Identity fields (name/email/avatar) are NOT stored here — lookup from
    Consumer via consumer_uid at render time.
    """
    teacher_id    = columns.UUID(partition_key=True)
    consumer_uid  = columns.UUID(primary_key=True, clustering_order="ASC")

    first_joined_at = columns.DateTime(default=datetime.utcnow)

    last_contact_at  = columns.DateTime(default=datetime.utcnow)
    last_contact_type = columns.Text(default='joined')
    last_contact_ref_id = columns.UUID(required=False)
    contact_count    = columns.Integer(default=1)

    __table_name__ = 'course_teacher_contacts'

    class Meta:
        get_pk_field = 'consumer_uid'
