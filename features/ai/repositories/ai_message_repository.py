import uuid
from datetime import datetime
from typing import List, Optional

from features.chat.models.message import Message
from core.utils.uuid import uuid7


class AIMessageRepository:
    """
    Reads and writes AI conversation messages to chat_messages.
    Uses session_id as conversation_uid to co-locate with chat infra.
    sender_type='user' for human turns, sender_type='ai' for bot turns.
    """

    @staticmethod
    def _safe_uuid(val) -> Optional[uuid.UUID]:
        if not val:
            return None
        try:
            return uuid.UUID(str(val))
        except (ValueError, TypeError, AttributeError):
            return None

    def add_user_message(self, session_id: str, content: str, user_id: str = None, user_name: str = '') -> None:
        conv_uid = self._safe_uuid(session_id)
        if not conv_uid:
            return
        Message.create(
            conversation_uid=conv_uid,
            uid=uuid7(),
            msg_type='text',
            content=content,
            sender_id=self._safe_uuid(user_id),
            sender_type='user',
            sender_name=user_name,
            created_at=datetime.utcnow(),
        )

    def add_ai_message(self, session_id: str, content: str) -> None:
        conv_uid = self._safe_uuid(session_id)
        if not conv_uid:
            return
        Message.create(
            conversation_uid=conv_uid,
            uid=uuid7(),
            msg_type='text',
            content=content,
            sender_type='ai',
            sender_name='AI Trợ giảng',
            created_at=datetime.utcnow(),
        )

    def get_all(self, session_id: str) -> List[Message]:
        conv_uid = self._safe_uuid(session_id)
        if not conv_uid:
            return []
        return list(
            Message.objects.filter(
                conversation_uid=conv_uid,
                is_deleted=False,
            ).limit(10000)
        )

    def get_display_messages(self, session_id: str) -> List[dict]:
        """Returns [{role, content}] ordered oldest-first for FE display."""
        msgs = self.get_all(session_id)
        result = []
        for m in reversed(msgs):  # Cassandra returns DESC; reverse to asc
            role = 'assistant' if m.sender_type == 'ai' else 'user'
            result.append({'role': role, 'content': m.content})
        return result

    def get_history_for_llm(self, session_id: str, max_turns: int = 5) -> List[dict]:
        """Returns last max_turns [{role, content}] for LLM context window."""
        all_msgs = self.get_display_messages(session_id)
        max_msgs = max_turns * 2
        return all_msgs[-max_msgs:] if len(all_msgs) > max_msgs else all_msgs

    def count_turns(self, session_id: str) -> int:
        """Number of user turns (question count)."""
        msgs = self.get_all(session_id)
        return sum(1 for m in msgs if m.sender_type == 'user')

    def is_first_message(self, session_id: str) -> bool:
        conv_uid = self._safe_uuid(session_id)
        if not conv_uid:
            return True
        existing = Message.objects.filter(
            conversation_uid=conv_uid,
            is_deleted=False,
        ).limit(1)
        return len(list(existing)) == 0
