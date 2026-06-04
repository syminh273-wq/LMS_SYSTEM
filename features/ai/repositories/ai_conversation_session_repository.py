import uuid
from datetime import datetime
from typing import List, Optional

from features.ai.models.ai_conversation_session import AIConversationSession


class AIConversationSessionRepository:

    @staticmethod
    def _safe_uuid(val) -> Optional[uuid.UUID]:
        if not val:
            return None
        try:
            return uuid.UUID(str(val))
        except (ValueError, TypeError, AttributeError):
            return None

    def create(self, user_id, classroom_id=None) -> AIConversationSession:
        kwargs = {
            'bucket': 0,
            'user_id': self._safe_uuid(user_id),
            'title': '',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        if classroom_id:
            kwargs['classroom_id'] = self._safe_uuid(classroom_id)
        return AIConversationSession.create(**kwargs)

    def find(self, session_id) -> Optional[AIConversationSession]:
        uid = self._safe_uuid(session_id)
        if not uid:
            return None
        return AIConversationSession.objects.filter(
            bucket=0,
            session_id=uid,
        ).allow_filtering().first()

    def list_by_user_classroom(self, user_id, classroom_id) -> List[AIConversationSession]:
        u_uid = self._safe_uuid(user_id)
        c_uid = self._safe_uuid(classroom_id)
        if not u_uid or not c_uid:
            return []
        return list(
            AIConversationSession.objects.filter(
                bucket=0,
                user_id=u_uid,
                classroom_id=c_uid,
                is_deleted=False,
            ).allow_filtering()
        )

    def set_title(self, session_id, title: str) -> None:
        uid = self._safe_uuid(session_id)
        if not uid:
            return
        AIConversationSession.objects.filter(
            bucket=0,
            session_id=uid,
        ).update(title=title[:80])

    def touch(self, session_id) -> None:
        uid = self._safe_uuid(session_id)
        if not uid:
            return
        AIConversationSession.objects.filter(
            bucket=0,
            session_id=uid,
        ).update(updated_at=datetime.utcnow())

    def soft_delete(self, session_id) -> None:
        uid = self._safe_uuid(session_id)
        if not uid:
            return
        AIConversationSession.objects.filter(
            bucket=0,
            session_id=uid,
        ).update(
            is_deleted=True,
            deleted_at=datetime.utcnow(),
        )
