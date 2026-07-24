from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Conversation(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    type = columns.Text(default='channel')             # 'channel' | 'direct'
    classroom_uid = columns.UUID(index=True, required=False)
    name = columns.Text(default='')
    description = columns.Text(default='')
    direct_a_id = columns.UUID(index=True, required=False)  # smaller UUID
    direct_b_id = columns.UUID(index=True, required=False)  # larger UUID
    pair_key = columns.Text(index=True, required=False, default='')  # sorted "emailA|emailB" canonical key
    member_count = columns.Integer(default=0)
    last_msg_at = columns.DateTime(required=False)
    last_msg_text = columns.Text(default='')
    last_msg_sender = columns.Text(default='')
    created_by_id = columns.UUID(required=False)

    __table_name__ = 'chat_conversations'

    class Meta:
        get_pk_field = 'uid'
