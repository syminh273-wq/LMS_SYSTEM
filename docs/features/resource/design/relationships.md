# Resource Module — Entity Relationships

## Relationship Map

```
Consumer / Space (account module)
    │
    └── Resource (1:N via owner_id + owner_type)
              │
              ├── → Exam.resource_uid        (file-based exams)
              ├── → Message.resource_uid     (file messages in chat)
              └── → Submission.resource_uid  (student file submissions)
```

---

## Detailed Relationship Descriptions

### 1. Consumer / Space → Resource
**Type**: One-to-Many (polymorphic via `owner_type`)

**Business Meaning**: Any authenticated user — teacher or student — can upload files. The `owner_id` and `owner_type` fields together identify the uploader. This allows the platform to enforce that only the owner can list and delete their own resources.

---

### 2. Resource → Exam (cross-module)
**Type**: One-to-One (per exam)

**Business Meaning**: When a teacher creates a file-based exam (PDF, image, or generic file), they reference a `resource_uid` that was previously uploaded. The Exam record caches `resource_url` and `resource_name` at creation time.

---

### 3. Resource → Message (cross-module)
**Type**: One-to-Many

**Business Meaning**: File messages in chat store `resource_uid`, `resource_url`, `resource_name`, and `resource_size` on the message record. The Resource module is the authoritative source, but chat caches the display data for performance.

---

## Cross-Module References

| Consumer of Resource | Field | Usage |
|---|---|---|
| Exam | `resource_uid`, `resource_url`, `resource_name` | Attach uploaded file to exam |
| Message | `resource_uid`, `resource_url`, `resource_name`, `resource_size` | Attach file to chat message |
| Submission *(planned)* | `resource_uid`, `resource_url`, `resource_name` | Student submits uploaded file |
