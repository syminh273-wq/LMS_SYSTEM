# Account Module — Entity Relationships

## Relationship Map

```
AbstractAuthModel (Abstract)
    │
    ├──── Consumer ──────────────── → ClassroomMember (member_id)
    │          │
    │          └──────────────────── → Conversation (direct_a_id / direct_b_id)
    │
    └──── Space ─────────────────── → Classroom (teacher_id)
               │
               └──────────────────── → ClassroomMember (member_id, role=teacher)
```

---

## Detailed Relationship Descriptions

### 1. AbstractAuthModel → Consumer, Space
**Type**: Inheritance (abstract parent)

**Business Meaning**: Both account types share the same foundational identity contract. This ensures consistent authentication behavior — password hashing, active/verified checks, DRF compatibility — without duplicating logic. The abstract model enforces that any new account type added in the future will conform to the same contract.

---

### 2. Consumer → ClassroomMember
**Type**: One-to-Many (one Consumer can be a member of many classrooms)

**Business Meaning**: When a student joins a classroom, a `ClassroomMember` record is created with `member_id = consumer.uid` and `role = student`. The member record also caches `member_name` and `member_avatar` from the Consumer at join time to avoid cross-table lookups during member list queries.

**Key Constraint**: A Consumer can only appear once per classroom. Duplicate membership is rejected at the service level.

---

### 3. Space → Classroom
**Type**: One-to-Many (one Space owns many classrooms)

**Business Meaning**: A Space account is the owner of all classrooms it creates. The `classroom.teacher_id` field stores `space.uid`. Ownership determines who can edit, publish, or delete the classroom and its content.

**Key Constraint**: A classroom has exactly one owner (teacher). Ownership cannot be transferred.

---

### 4. Space → ClassroomMember
**Type**: One-to-Many (Space may appear as a member in its own classrooms)

**Business Meaning**: When a Space creates a classroom, it may also be added as a member with `role = teacher`. This allows the teacher to participate in classroom chat and other member-scoped features.

---

## Cross-Module Relationships

| Entity (Account) | Entity (External Module) | Relationship | Business Meaning |
|---|---|---|---|
| `Consumer.uid` | `ClassroomMember.member_id` | Many-to-Many via ClassroomMember | Students join classrooms |
| `Space.uid` | `Classroom.teacher_id` | One-to-Many | Space owns classrooms |
| `Consumer.uid` | `Conversation.direct_a_id / direct_b_id` | Many-to-Many via Conversation | Students participate in direct chats |
| `Consumer.uid` | `Resource.owner_id` | One-to-Many | Consumers own uploaded resources |
| `Space.uid` | `Resource.owner_id` | One-to-Many | Spaces own uploaded resources |
