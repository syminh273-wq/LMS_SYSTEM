import uuid as _uuid
from datetime import datetime
from features.chat.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(self):
        self.repo = ConversationRepository()

    def get_or_create_channel(self, classroom_uid, name='Thảo luận chung', created_by_id=None):
        existing = list(self.repo.get_by_classroom(classroom_uid))
        if existing:
            return existing[0]
        return self.repo.create(
            classroom_uid=_uuid.UUID(str(classroom_uid)),
            type='channel',
            name=name,
            member_count=0,
            created_by_id=_uuid.UUID(str(created_by_id)) if created_by_id else None,
        )

    def get_or_create_direct(self, user_a_id, user_b_id):
        ids = sorted([str(user_a_id), str(user_b_id)])
        existing = self.repo.get_direct(ids[0], ids[1])
        if existing:
            return existing, False
        conv = self.repo.create(
            type='direct',
            direct_a_id=_uuid.UUID(ids[0]),
            direct_b_id=_uuid.UUID(ids[1]),
            member_count=2,
        )
        return conv, True

    def get_channels_by_classroom(self, classroom_uid):
        return list(self.repo.get_by_classroom(classroom_uid))

    def update_last_message(self, conversation_uid, text, sender_name):
        from features.chat.models.conversation import Conversation
        conv = Conversation.objects.filter(
            uid=_uuid.UUID(str(conversation_uid))
        ).allow_filtering().first()
        if conv:
            conv.update(
                last_msg_text=text[:100] if text else '',
                last_msg_sender=sender_name,
                last_msg_at=datetime.utcnow(),
            )
