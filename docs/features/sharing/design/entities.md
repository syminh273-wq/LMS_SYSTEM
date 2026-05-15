# Sharing Module — Entities

---

## 1. Link

**Purpose**: A shareable short-code URL that points to a resource and triggers an action when accessed.

**Table**: `sharing_links`

| Column | Type | Key | Description |
|---|---|---|---|
| `uid` | UUID v7 | Primary key | Link identifier |
| `code` | Text | Indexed | Unique short code used in the share URL |
| `resource_type` | Text | Indexed | Type of the linked resource (e.g., `classroom`) |
| `resource_id` | UUID | Indexed | ID of the linked resource |
| `action` | Text | — | Action to execute on access (e.g., `join`) |
| `expired_at` | DateTime | — | Expiry timestamp; `null` = never expires |
| `max_usage` | Integer | — | Max number of uses; `0` = unlimited |
| `used_count` | Integer | — | Current usage count |
| `is_active` | Boolean | Indexed | Whether the link is currently active |
| `metadata` | Map<Text, Text> | — | Arbitrary extra data |
| `created_at` | DateTime | — | |
| `updated_at` | DateTime | — | |
| `is_deleted` | Boolean | — | Soft delete flag |
| `deleted_at` | DateTime | — | |

---

## 2. ResourceType (Enum)

**Purpose**: Enumerates supported resource types for linking.

| Value | Description |
|---|---|
| `classroom` | Invite link for a classroom |
