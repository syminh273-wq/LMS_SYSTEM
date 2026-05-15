# Chat Module — Entities

---

## 1. Conversation

**Purpose**: A chat room. Either a classroom channel or a 1-to-1 direct message thread.

**Table**: `chat_conversations`

| Column | Type | Key | Description |
|---|---|---|---|
| `bucket` | Integer | Partition key | Distribution bucket (default `0`) |
| `uid` | UUID v7 | Clustering key DESC | Time-ordered conversation identifier |
| `type` | Text | — | `channel` \| `direct` |
| `classroom_uid` | UUID | Indexed | Linked classroom *(channel type only)* |
| `name` | Text | — | Display name |
| `description` | Text | — | |
| `direct_a_id` | UUID | Indexed | Smaller of the two participant UIDs *(direct only)* |
| `direct_b_id` | UUID | Indexed | Larger of the two participant UIDs *(direct only)* |
| `member_count` | Integer | — | Cached participant count |
| `last_msg_at` | DateTime | — | Timestamp of last message *(cached)* |
| `last_msg_text` | Text | — | Preview of last message text *(cached)* |
| `last_msg_sender` | Text | — | Sender name of last message *(cached)* |
| `created_by_id` | UUID | — | Creator's uid |
| `created_at` | DateTime | — | |
| `is_deleted` | Boolean | — | Soft delete flag |

---

## 2. Message

**Purpose**: A single message within a conversation. Supports text and file attachments.

**Table**: `chat_messages`

| Column | Type | Key | Description |
|---|---|---|---|
| `conversation_uid` | UUID | Partition key | Groups all messages of a conversation |
| `uid` | UUID v7 | Clustering key DESC | Time-ordered message identifier |
| `msg_type` | Text | — | `text` \| `image` \| `video` \| `audio` \| `pdf` \| `file` |
| `content` | Text | — | Text body *(msg_type=text)* |
| `sender_id` | UUID | — | Sender's uid |
| `sender_type` | Text | — | `consumer` \| `space` |
| `sender_name` | Text | — | Cached sender display name |
| `resource_uid` | UUID | — | Referenced resource *(file types)* |
| `resource_url` | Text | — | Cached file URL |
| `resource_name` | Text | — | Cached filename |
| `resource_size` | BigInt | — | Cached file size in bytes |
| `reply_to_uid` | UUID | — | UID of message being replied to |
| `is_deleted` | Boolean | — | Soft delete flag |
| `created_at` | DateTime | — | |
