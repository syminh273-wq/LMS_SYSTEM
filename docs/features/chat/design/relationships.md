# Chat Module — Entity Relationships

## Relationship Map

```
Classroom (course module)
    └── Conversation (1:1 via classroom_uid, type=channel)
              │
              └── Message (1:N via conversation_uid)
                      │
                      └── → Resource.uid (resource_uid, optional)

Consumer / Space (account module)
    └── Conversation (M:N via direct_a_id / direct_b_id, type=direct)
              │
              └── Message (1:N, sender_id)
```

---

## Detailed Relationship Descriptions

### 1. Classroom → Conversation (Channel)
**Type**: One-to-One

**Business Meaning**: Every classroom has exactly one channel conversation created automatically. The `classroom_uid` field links the conversation to its classroom. Classroom members become conversation participants.

---

### 2. Consumer / Space → Conversation (Direct)
**Type**: Many-to-Many (via sorted UID pair)

**Business Meaning**: Any two users can have a direct message thread. The pair is stored as `(direct_a_id, direct_b_id)` with the smaller UUID always in `direct_a_id`. This ensures a unique, deterministic lookup for any user pair without the risk of creating duplicate conversations.

---

### 3. Conversation → Message
**Type**: One-to-Many (partitioned)

**Business Meaning**: Messages belong to a conversation. The partition key `conversation_uid` places all messages of a conversation in the same Cassandra partition, enabling efficient full-history queries with a single partition scan. The clustering key `uid DESC` returns messages in reverse chronological order.

---

### 4. Message → Resource (optional)
**Type**: Zero-or-One

**Business Meaning**: File messages carry a `resource_uid` referencing the uploaded file. The URL, name, and size are cached directly on the message row so that displaying the message requires no additional lookup.

---

## Cross-Module Relationships

| Entity (Chat) | Entity (External) | Relationship | Business Meaning |
|---|---|---|---|
| `Conversation.classroom_uid` | `Classroom.uid` | One-to-One | Channel is scoped to a classroom |
| `Message.sender_id` | `Consumer.uid` / `Space.uid` | Many-to-One | Message has a sender |
| `Message.resource_uid` | `Resource.uid` | Many-to-One (optional) | File message references uploaded resource |
