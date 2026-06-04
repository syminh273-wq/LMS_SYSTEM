from typing import List, Optional

from features.ai.repositories.ai_conversation_session_repository import AIConversationSessionRepository
from features.ai.repositories.ai_message_repository import AIMessageRepository

_session_repo = AIConversationSessionRepository()
_msg_repo = AIMessageRepository()


class AIConversationSessionService:

    def create_session(self, user_id, classroom_id=None) -> str:
        session = _session_repo.create(user_id=user_id, classroom_id=classroom_id)
        return str(session.session_id)

    def ensure_session(self, session_id: Optional[str], user_id: str, classroom_id: str = None) -> str:
        if session_id and self.session_exists(session_id):
            return session_id
        existing = self.list_sessions(user_id, classroom_id)
        if existing:
            return existing[0]['session_id']
        return self.create_session(user_id, classroom_id)

    def get_history(self, session_id: str) -> List[dict]:
        """Last 5 turns for LLM context (10 messages)."""
        return _msg_repo.get_history_for_llm(session_id, max_turns=5)

    def get_display_messages(self, session_id: str) -> List[dict]:
        """Full message list for FE display."""
        return _msg_repo.get_display_messages(session_id)

    def save_turn(self, session_id: str, question: str, answer: str) -> None:
        is_first = _msg_repo.is_first_message(session_id)
        if is_first:
            _session_repo.set_title(session_id, question[:80])
        _msg_repo.add_user_message(session_id, question)
        _msg_repo.add_ai_message(session_id, answer)
        _session_repo.touch(session_id)

    def list_sessions(self, user_id, classroom_id) -> List[dict]:
        sessions = _session_repo.list_by_user_classroom(user_id=user_id, classroom_id=classroom_id)
        result = []
        for s in sessions:
            result.append({
                'session_id': str(s.session_id),
                'title':      s.title or 'Hội thoại mới',
                'msg_count':  _msg_repo.count_turns(str(s.session_id)),
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                'created_at': s.created_at.isoformat() if s.created_at else None,
            })
        result.sort(key=lambda x: x['updated_at'] or '', reverse=True)
        return result

    def clear_session(self, session_id: str, user_id, classroom_id=None) -> str:
        _session_repo.soft_delete(session_id)
        return self.create_session(user_id=user_id, classroom_id=classroom_id)

    def session_exists(self, session_id: str) -> bool:
        session = _session_repo.find(session_id)
        return session is not None and not session.is_deleted
