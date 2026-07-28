from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class Attendance(BaseTimeStampModel):
    """One row per (event, user).

    Composite primary key: (event_id partition, user_id clustering).
    django_cassandra_engine requires get_pk_field on composite-key
    models for .get(pk=...) routing; event_id is the natural partition.
    """

    event_id = columns.UUID(partition_key=True, primary_key=True, required=True)
    user_id  = columns.UUID(primary_key=True, required=True)

    status    = columns.Text(default='absent', index=True)
    joined_at = columns.DateTime(required=False)
    left_at   = columns.DateTime(required=False)

    date = columns.Date(index=True)

    class Meta:
        get_pk_field = 'event_id'

    __table_name__ = 'calendar_attendances'
