from datetime import datetime
from core.repositories.base_repository import BaseRepository
from features.chat.models.conversation_member import ConversationMember


class ConversationMemberRepository(BaseRepository):
    model = ConversationMember

    def get_members(self, conversation_uid):
        return self.model.objects.filter(
            conversation_uid=conversation_uid,
            is_deleted=False,
        )

    def get_member(self, conversation_uid, member_id):
        try:
            return self.model.objects.get(
                conversation_uid=conversation_uid,
                member_id=member_id,
            )
        except Exception:
            return None

    def update_last_read(self, conversation_uid, member_id, msg_uid):
        m = self.get_member(conversation_uid, member_id)
        if m:
            m.update(
                last_read_msg_uid=msg_uid,
                last_seen_at=datetime.utcnow(),
            )

    def update_last_seen(self, conversation_uid, member_id):
        m = self.get_member(conversation_uid, member_id)
        if m:
            m.update(last_seen_at=datetime.utcnow())
