from datetime import datetime

from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class AIConversationSession(DjangoCassandraModel):
    """Session metadata only. Messages are stored in chat_messages (sender_type='ai'|'user')."""
    bucket       = columns.Integer(partition_key=True, default=0)
    session_id   = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    user_id      = columns.UUID(index=True)
    classroom_id = columns.UUID(index=True, required=False)
    title        = columns.Text(default='')
    created_at   = columns.DateTime(default=datetime.utcnow)
    updated_at   = columns.DateTime(default=datetime.utcnow)
    is_deleted   = columns.Boolean(default=False)
    deleted_at   = columns.DateTime(required=False)

    __table_name__ = 'ai_conversation_sessions'

    class Meta:
        get_pk_field = 'session_id'
