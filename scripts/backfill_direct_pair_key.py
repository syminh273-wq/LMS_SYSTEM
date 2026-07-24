"""Backfill pair_key cho conversation cũ + gộp conversation trùng người (cùng email).

Logic:
- Quét tất cả conversation direct có pair_key rỗng
- Tính pair_key từ email của direct_a_id + direct_b_id
- Nếu đã có conversation khác cùng pair_key → gộp messages + members vào conversation cũ (giữ conv có last_msg_at mới nhất), xóa conv trùng
- Nếu chưa có → set pair_key cho conv hiện tại

Chạy: python manage.py shell < scripts/backfill_direct_pair_key.py
"""
from features.chat.models.conversation import Conversation
from features.chat.models.conversation_member import ConversationMember
from features.chat.models.message import Message
from features.chat.services.identity_resolver import _email_for_uid
import uuid

# 1. Lấy tất cả direct conversations có pair_key rỗng
convs = list(Conversation.objects.filter(type='direct', is_deleted=False).allow_filtering())
print(f'Total direct conversations: {len(convs)}')

# 2. Group theo pair_key
groups: dict[str, list] = {}
unkeyed = []
for c in convs:
    if c.pair_key:
        continue
    email_a = _email_for_uid(c.direct_a_id)
    email_b = _email_for_uid(c.direct_b_id)
    if not email_a or not email_b:
        unkeyed.append(c)
        continue
    pair = sorted([email_a, email_b])
    pk = f'{pair[0]}|{pair[1]}'
    groups.setdefault(pk, []).append(c)

print(f'Unkeyed (missing email): {len(unkeyed)}')
print(f'Grouped: {len(groups)} pair_keys, {sum(len(v) for v in groups.values())} conversations')

# 3. Với mỗi group: giữ conv mới nhất, các conv còn lại chuyển messages/members sang conv giữ, đánh dấu is_deleted
moved_msgs = 0
moved_members = 0
deleted_convs = 0
updated_convs = 0

for pk, conv_list in groups.items():
    if len(conv_list) == 1:
        c = conv_list[0]
        c.update(pair_key=pk)
        updated_convs += 1
        continue

    conv_list.sort(key=lambda x: x.last_msg_at or x.created_at or datetime.min, reverse=True)
    keep = conv_list[0]
    keep.update(pair_key=pk)
    updated_convs += 1

    for dup in conv_list[1:]:
        # move messages
        msgs = list(Message.objects.filter(conversation_uid=dup.uid, is_deleted=False).allow_filtering())
        for m in msgs:
            m.update(conversation_uid=keep.uid)
            moved_msgs += 1
        # move members
        members = list(ConversationMember.objects.filter(conversation_uid=dup.uid, is_deleted=False))
        for mem in members:
            existing = list(ConversationMember.objects.filter(
                conversation_uid=keep.uid, member_id=mem.member_id
            ).allow_filtering().limit(1))
            if not existing:
                ConversationMember.create(
                    conversation_uid=keep.uid,
                    member_id=mem.member_id,
                    member_type=mem.member_type,
                    member_name=mem.member_name,
                    member_avatar=mem.member_avatar,
                    joined_at=mem.joined_at or mem.created_at,
                    last_seen_at=mem.last_seen_at,
                    last_read_msg_uid=mem.last_read_msg_uid,
                )
                moved_members += 1
            else:
                # giữ last_seen_at mới nhất
                if mem.last_seen_at and (not existing[0].last_seen_at or mem.last_seen_at > existing[0].last_seen_at):
                    existing[0].update(last_seen_at=mem.last_seen_at, last_read_msg_uid=mem.last_read_msg_uid or existing[0].last_read_msg_uid)
        dup.update(is_deleted=True, deleted_at=datetime.utcnow())
        deleted_convs += 1

# 4. Unkeyed (không có email) → set pair_key dạng uid
for c in unkeyed:
    pk = f'uid:{c.direct_a_id}|uid:{c.direct_b_id}'
    c.update(pair_key=pk)
    updated_convs += 1

print(f'Updated pair_key: {updated_convs}')
print(f'Moved messages: {moved_msgs}')
print(f'Moved members: {moved_members}')
print(f'Deleted duplicate conversations: {deleted_convs}')
print('DONE')
