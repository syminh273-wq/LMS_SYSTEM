from typing import Optional, Sequence

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple

from features.ai.repositories.ai_conversation_session_repository import AIConversationSessionRepository
from features.ai.repositories.ai_message_repository import AIMessageRepository

_session_repo = AIConversationSessionRepository()
_msg_repo = AIMessageRepository()


class CassandraSaver(BaseCheckpointSaver):
    """LangGraph checkpointer backed by chat_messages table."""

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        session_id = config.get('configurable', {}).get('thread_id')
        if not session_id:
            return None

        session = _session_repo.find(session_id)
        if not session or session.is_deleted:
            return None

        raw = _msg_repo.get_display_messages(session_id)
        messages = []
        for m in raw:
            if m['role'] == 'user':
                messages.append(HumanMessage(content=m['content']))
            elif m['role'] == 'assistant':
                messages.append(AIMessage(content=m['content']))

        checkpoint = Checkpoint(
            v=1,
            id=str(session.session_id),
            ts=session.updated_at.isoformat(),
            channel_values={'messages': messages},
            channel_versions={},
            versions_seen={},
            pending_sends=[],
        )
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=CheckpointMetadata(source='cassandra'),
        )

    def put(self, config: dict, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> dict:
        session_id = config.get('configurable', {}).get('thread_id')
        if not session_id:
            return {}

        messages = checkpoint['channel_values'].get('messages', [])
        for m in messages:
            if isinstance(m, HumanMessage):
                _msg_repo.add_user_message(session_id, m.content)
            elif isinstance(m, (AIMessage,)):
                _msg_repo.add_ai_message(session_id, m.content)
        _session_repo.touch(session_id)
        return {}

    def list(self, config: dict, *, before: Optional[CheckpointTuple] = None, limit: Optional[int] = None) -> Sequence[CheckpointTuple]:
        return []
