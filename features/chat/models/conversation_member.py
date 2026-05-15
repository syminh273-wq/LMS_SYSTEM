from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class ConversationMember(DjangoCassandraModel):
    conversation_uid = columns.UUID(partition_key=True)
    member_id = columns.UUID(primary_key=True, clustering_order="ASC")
    member_type = columns.Text(default='consumer')
    member_name = columns.Text(default='')
    member_avatar = columns.Text(default='')
    joined_at = columns.DateTime(default=datetime.utcnow)
    last_seen_at = columns.DateTime(required=False)
    last_read_msg_uid = columns.UUID(required=False)
    is_deleted = columns.Boolean(default=False)

    __table_name__ = 'chat_conversation_members'

    class Meta:
        get_pk_field = 'member_id'
