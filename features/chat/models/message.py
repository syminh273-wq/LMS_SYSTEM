from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel
from core.utils.uuid import uuid7


class Message(DjangoCassandraModel):
    conversation_uid = columns.UUID(partition_key=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    msg_type = columns.Text(default='text')   # 'text'|'image'|'video'|'audio'|'pdf'|'file'
    content = columns.Text(default='')
    sender_id = columns.UUID(required=False)
    sender_type = columns.Text(default='')
    sender_name = columns.Text(default='')
    resource_uid = columns.UUID(required=False)
    resource_url = columns.Text(default='')
    resource_name = columns.Text(default='')
    resource_size = columns.BigInt(default=0)
    reply_to_uid = columns.UUID(required=False)
    is_deleted = columns.Boolean(default=False)
    created_at = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'chat_messages'

    class Meta:
        get_pk_field = 'uid'
