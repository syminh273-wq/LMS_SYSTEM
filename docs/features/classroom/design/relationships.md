# Classroom Module — Entity Relationships

## Relationship Map

```
Space (account module)
    │
    └── Classroom (1:N via teacher_id)
              │
              ├── ClassroomMember (1:N via classroom_uid)
              │         │
              │         └── → Consumer.uid  (member_type = consumer)
              │         └── → Space.uid     (member_type = space, role = teacher)
              │
              └── Link (0:1 via resource_id, Sharing module)
```

---

## Detailed Relationship Descriptions

### 1. Space → Classroom
**Type**: One-to-Many

**Business Meaning**: A Space account owns all classrooms it creates. The `teacher_id` field on `Classroom` stores the owning Space's uid. This relationship is the primary authorization boundary — only the owning Space can modify or delete the classroom.

**Constraint**: One classroom has exactly one owner. No transfer of ownership.

---

### 2. Classroom → ClassroomMember
**Type**: One-to-Many (partitioned by `classroom_uid`)

**Business Meaning**: A classroom has many members. The partition key `classroom_uid` groups all members together in Cassandra, making member list scans an efficient single-partition read. The clustering key `member_id ASC` ensures deterministic ordering.

**Constraint**: A user can only appear once per classroom. Duplicate `(classroom_uid, member_id)` pairs are rejected.

---

### 3. ClassroomMember → Consumer / Space
**Type**: Many-to-One (polymorphic via `member_type`)

**Business Meaning**: A membership record can belong to either a Consumer (student) or a Space (teacher). The `member_type` field disambiguates which account table to look up when full profile data is needed. Because `member_name` and `member_avatar` are cached on the record, most member list operations do not require a lookup.

---

### 4. Classroom → Link (Sharing Module)
**Type**: Zero-or-One (optional)

**Business Meaning**: A classroom may have one active sharing link. The link is not stored on the Classroom record — it is fetched lazily via `resolve_link` from the Sharing module. A classroom without a link returns `null` for this field.

---

## Cross-Module Relationships

| Entity (Classroom) | Entity (External) | Relationship | Business Meaning |
|---|---|---|---|
| `Classroom.teacher_id` | `Space.uid` | Many-to-One | Space owns the classroom |
| `ClassroomMember.member_id` | `Consumer.uid` | Many-to-One | Consumer is a student member |
| `ClassroomMember.member_id` | `Space.uid` | Many-to-One | Space participates as teacher member |
| `Classroom.uid` | `Link.resource_id` | One-to-Zero-or-One | Classroom may have one invite link |
| `Classroom.uid` | `Conversation.classroom_uid` | One-to-One | Each classroom has a channel conversation |
