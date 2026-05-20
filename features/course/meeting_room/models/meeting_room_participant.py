from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class MeetingRoomParticipant(DjangoCassandraModel):
    room_uid = columns.UUID(partition_key=True)
    participant_id = columns.UUID(primary_key=True, clustering_order="DESC")

    participant_type = columns.Text(default='consumer')        # 'space' | 'consumer'
    participant_name = columns.Text(default='')
    participant_avatar = columns.Text(default='')

    role = columns.Text(default='participant')                 # 'host' | 'participant'

    joined_at = columns.DateTime(default=datetime.utcnow)
    left_at = columns.DateTime(required=False)
    is_deleted = columns.Boolean(default=False)

    __table_name__ = 'course_meeting_room_participants'

    class Meta:
        get_pk_field = 'participant_id'
