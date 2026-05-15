import uuid as _uuid
from features.chat.repositories.conversation_member_repository import ConversationMemberRepository


class ConversationMemberService:
    def __init__(self):
        self.repo = ConversationMemberRepository()

    def add_member(self, conversation_uid, user):
        name = getattr(user, 'full_name', '') or getattr(user, 'username', '') or ''
        avatar = getattr(user, 'avatar_url', '') or getattr(user, 'logo_url', '') or ''
        member_type = 'space' if hasattr(user, 'logo_url') else 'consumer'
        existing = self.repo.get_member(
            _uuid.UUID(str(conversation_uid)), user.uid
        )
        if existing and not existing.is_deleted:
            return existing
        return self.repo.create(
            conversation_uid=_uuid.UUID(str(conversation_uid)),
            member_id=user.uid,
            member_type=member_type,
            member_name=name,
            member_avatar=avatar,
        )

    def get_members(self, conversation_uid):
        return list(self.repo.get_members(_uuid.UUID(str(conversation_uid))))

    def update_last_seen(self, conversation_uid, member_id):
        try:
            self.repo.update_last_seen(
                _uuid.UUID(str(conversation_uid)),
                _uuid.UUID(str(member_id)),
            )
        except Exception:
            pass

    def mark_read(self, conversation_uid, member_id, msg_uid):
        try:
            self.repo.update_last_read(
                _uuid.UUID(str(conversation_uid)),
                _uuid.UUID(str(member_id)),
                _uuid.UUID(str(msg_uid)),
            )
        except Exception:
            pass
