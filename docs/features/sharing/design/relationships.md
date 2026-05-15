# Sharing Module — Entity Relationships

## Relationship Map

```
Link
  └── → Classroom.uid    (resource_type=classroom, resource_id=classroom.uid)
  └── → [Future resources] (resource_type=event, resource_type=file, etc.)
```

---

## Detailed Relationship Descriptions

### 1. Link → Classroom
**Type**: Many-to-Zero-or-One (a classroom may have multiple links; each link points to one classroom)

**Business Meaning**: A teacher can create multiple invite links for the same classroom (e.g., one for each batch of students, with different expiry dates). Each link is independent. The classroom is unaware of how many links point to it — the relationship is managed entirely by the Sharing module.

**Integration**: When a link with `resource_type=classroom` is accessed, `LinkService` calls `ClassroomMemberService.add_member()` with the consumer's uid and the classroom uid from `resource_id`.

---

## Cross-Module Relationships

| Entity (Sharing) | Entity (External) | Relationship | Business Meaning |
|---|---|---|---|
| `Link.resource_id` | `Classroom.uid` | Many-to-One (by value) | Link points to a classroom |
| `Link` | `ClassroomMember` | Triggers creation | Accessing the link creates a membership |
