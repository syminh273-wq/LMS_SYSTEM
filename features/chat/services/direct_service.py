import uuid
from datetime import datetime

from features.chat.models.conversation import Conversation
from features.chat.models.conversation_member import ConversationMember
from features.chat.models.message import Message
from features.chat.services.identity_resolver import pair_key as build_pair_key, _email_for_uid
from features.chat.services.conversation_service import ConversationService


def _serialize_direct(conv: Conversation, other_member: ConversationMember, unread: int, last_msg: dict | None) -> dict:
    return {
        'conversation_uid': str(conv.uid),
        'other_user': {
            'uid': str(other_member.member_id),
            'name': other_member.member_name or '',
            'avatar': other_member.member_avatar or '',
            'last_seen_at': other_member.last_seen_at.isoformat() if other_member.last_seen_at else None,
        },
        'last_msg': last_msg or {},
        'unread_count': unread,
        'created_at': conv.created_at.isoformat() if conv.created_at else None,
    }


def _fetch_unread(conv_uid, member_id, last_read_msg_uid) -> int:
    qs = Message.objects.filter(conversation_uid=conv_uid, is_deleted=False)
    if last_read_msg_uid:
        try:
            qs = Message.objects.filter(conversation_uid=conv_uid, is_deleted=False, uid__gt=last_read_msg_uid)
        except Exception:
            pass
    return sum(1 for _ in qs)


def find_conversation_with_target(user_uid, target_uid):
    """Tìm conversation direct đã tồn tại giữa current user và target user (không tạo mới).

    Trả về dict {conversation_uid, other_user} hoặc None.
    Dùng canonical pair_key (email) để match cả 2 trường hợp UID khác nhau cùng 1 người.
    """
    pk = build_pair_key(user_uid, target_uid)
    repo = ConversationService().repo
    conv = repo.get_direct_by_pair_key(pk)
    if not conv:
        return None

    members = list(ConversationMember.objects.filter(conversation_uid=conv.uid, is_deleted=False))
    me = next((m for m in members if str(m.member_id) == str(user_uid)), None)
    other = next((m for m in members if str(m.member_id) != str(user_uid)), None)
    if not other:
        return None
    return {
        'conversation_uid': str(conv.uid),
        'other_user': {
            'uid': str(other.member_id),
            'name': other.member_name or '',
            'avatar': other.member_avatar or '',
        },
    }


def list_direct_conversations(user_uid) -> list[dict]:
    uid = uuid.UUID(str(user_uid))
    all_qs = Conversation.objects.filter(bucket=0, type='direct', is_deleted=False).allow_filtering()
    direct_a = list(all_qs.filter(direct_a_id=uid))
    direct_b = list(all_qs.filter(direct_b_id=uid))
    convs = direct_a + direct_b
    convs.sort(key=lambda c: c.last_msg_at or c.created_at or datetime.min, reverse=True)

    seen_pair_keys: set[str] = set()
    out = []
    for conv in convs:
        if conv.pair_key:
            if conv.pair_key in seen_pair_keys:
                continue
            seen_pair_keys.add(conv.pair_key)

        members = list(ConversationMember.objects.filter(conversation_uid=conv.uid, is_deleted=False))
        me = next((m for m in members if str(m.member_id) == str(uid)), None)
        other = next((m for m in members if str(m.member_id) != str(uid)), None)
        if not me or not other:
            continue
        unread = _fetch_unread(conv.uid, me.member_id, me.last_read_msg_uid)
        last_msg = None
        if conv.last_msg_at:
            last_msg = {
                'text': conv.last_msg_text or '',
                'sender_name': conv.last_msg_sender or '',
                'at': conv.last_msg_at.isoformat() if conv.last_msg_at else None,
            }
        out.append(_serialize_direct(conv, other, unread, last_msg))
    return out


def create_message(conversation_uid, sender_id, sender_name, sender_type: str,
                   content: str, msg_type: str = 'text',
                   resource_uid=None, resource_url='', resource_name='', resource_size=0) -> dict:
    conv = list(Conversation.objects.filter(bucket=0, uid=uuid.UUID(str(conversation_uid)), is_deleted=False).limit(1))
    if not conv:
        raise ValueError('Conversation not found')
    conv = conv[0]

    msg = Message.create(
        conversation_uid=conv.uid,
        msg_type=msg_type,
        content=content or '',
        sender_id=uuid.UUID(str(sender_id)),
        sender_type=sender_type,
        sender_name=sender_name or '',
        resource_url=resource_url or '',
        resource_name=resource_name or '',
        resource_size=int(resource_size or 0),
        resource_uid=uuid.UUID(str(resource_uid)) if resource_uid else None,
    )

    conv.update(
        last_msg_text=(content or '')[:100],
        last_msg_sender=sender_name or '',
        last_msg_at=datetime.utcnow(),
    )

    return {
        'uid': str(msg.uid),
        'conversation_uid': str(msg.conversation_uid),
        'msg_type': msg.msg_type,
        'content': msg.content or '',
        'sender_id': str(msg.sender_id) if msg.sender_id else None,
        'sender_type': msg.sender_type or '',
        'sender_name': msg.sender_name or '',
        'attachment': {
            'uid': str(msg.resource_uid) if msg.resource_uid else None,
            'url': msg.resource_url or '',
            'name': msg.resource_name or '',
            'size': int(msg.resource_size or 0),
            'type': msg.msg_type or 'file',
        } if (msg.resource_url or msg.resource_uid) else None,
        'created_at': msg.created_at.isoformat() if msg.created_at else None,
    }


def mark_conversation_seen(conversation_uid, member_id, msg_uid=None):
    try:
        members = list(ConversationMember.objects.filter(
            conversation_uid=uuid.UUID(str(conversation_uid)),
            member_id=uuid.UUID(str(member_id)),
        ).limit(1))
        if not members:
            return
        m = members[0]
        kw = {'last_seen_at': datetime.utcnow()}
        if msg_uid:
            try:
                kw['last_read_msg_uid'] = uuid.UUID(str(msg_uid))
            except Exception:
                pass
        m.update(**kw)
    except Exception:
        pass
