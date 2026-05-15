import uuid as _uuid
from features.chat.repositories.message_repository import MessageRepository


class MessageService:
    def __init__(self):
        self.repo = MessageRepository()

    def get_messages(self, conversation_uid, limit=30):
        msgs = list(self.repo.get_messages(
            _uuid.UUID(str(conversation_uid)), limit=limit
        ))
        return list(reversed(msgs))  # oldest first for FE

    def get_messages_before(self, conversation_uid, before_uid, limit=30):
        msgs = list(self.repo.get_before(
            _uuid.UUID(str(conversation_uid)),
            _uuid.UUID(str(before_uid)),
            limit=limit,
        ))
        return list(reversed(msgs))

    def save_message(
        self,
        conversation_uid,
        sender_id,
        sender_type,
        sender_name,
        msg_type='text',
        content='',
        resource_uid=None,
        resource_url='',
        resource_name='',
        resource_size=0,
    ):
        kwargs = dict(
            conversation_uid=_uuid.UUID(str(conversation_uid)),
            sender_id=_uuid.UUID(str(sender_id)),
            sender_type=sender_type,
            sender_name=sender_name,
            msg_type=msg_type,
            content=content or '',
            resource_url=resource_url or '',
            resource_name=resource_name or '',
            resource_size=int(resource_size) if resource_size else 0,
        )
        if resource_uid:
            kwargs['resource_uid'] = _uuid.UUID(str(resource_uid))
        return self.repo.create(**kwargs)
