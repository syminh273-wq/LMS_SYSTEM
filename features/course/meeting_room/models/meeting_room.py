from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class MeetingRoom(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    classroom_uid = columns.UUID(index=True, required=False)   # optional link to classroom
    title = columns.Text(required=True)
    description = columns.Text(default='')

    host_id = columns.UUID(index=True, required=True)
    host_type = columns.Text(default='space')                  # 'space' | 'consumer'
    host_name = columns.Text(default='')

    status = columns.Text(default='waiting')                   # 'waiting' | 'active' | 'ended'
    max_participants = columns.Integer(default=0)              # 0 = unlimited
    participant_count = columns.Integer(default=0)

    started_at = columns.DateTime(required=False)
    ended_at = columns.DateTime(required=False)

    __table_name__ = 'course_meeting_rooms'

    class Meta:
        get_pk_field = 'uid'
