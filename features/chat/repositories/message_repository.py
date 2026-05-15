from core.repositories.base_repository import BaseRepository
from features.chat.models.message import Message


class MessageRepository(BaseRepository):
    model = Message

    def get_messages(self, conversation_uid, limit=30):
        return self.model.objects.filter(
            conversation_uid=conversation_uid,
            is_deleted=False,
        ).limit(limit)

    def get_before(self, conversation_uid, before_uid, limit=30):
        return self.model.objects.filter(
            conversation_uid=conversation_uid,
            is_deleted=False,
            uid__lt=before_uid,
        ).limit(limit)
