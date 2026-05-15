import uuid
from core.repositories.base_repository import BaseRepository
from features.chat.models.conversation import Conversation


class ConversationRepository(BaseRepository):
    model = Conversation

    def get_by_classroom(self, classroom_uid):
        return self.model.objects.filter(
            classroom_uid=classroom_uid,
            is_deleted=False,
        ).allow_filtering()

    def get_direct(self, a_id, b_id):
        ids = sorted([str(a_id), str(b_id)])
        return self.model.objects.filter(
            direct_a_id=uuid.UUID(ids[0]),
            direct_b_id=uuid.UUID(ids[1]),
            type='direct',
        ).allow_filtering().first()
