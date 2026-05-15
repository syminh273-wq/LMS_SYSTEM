# Classroom Module — Entities

---

## 1. Classroom

**Purpose**: Represents a learning room owned by a teacher. All content (exams, announcements) belongs to a classroom.

**Table**: `account_classrooms`

| Column | Type | Key | Description |
|---|---|---|---|
| `bucket` | Integer | Partition key | Distribution bucket (default `0`) |
| `uid` | UUID v7 | Clustering key DESC | Time-ordered classroom identifier |
| `pid` | Text | Indexed | Public short identifier |
| `name` | Text | — | Classroom display name *(required)* |
| `description` | Text | — | Optional description |
| `teacher_id` | UUID | Indexed | Owner — references `Space.uid` |
| `max_students` | Integer | — | Student cap; `0` = unlimited |
| `status` | Text | — | `active` \| `inactive` |
| `created_at` | DateTime | — | |
| `updated_at` | DateTime | — | |
| `is_deleted` | Boolean | — | Soft delete flag |
| `deleted_at` | DateTime | — | |

**Computed Property**:
- `resolve_link` (`@cached_property`) — Returns the associated sharing link from the Sharing module, or `None`.

---

## 2. ClassroomMember

**Purpose**: Records the membership of a user (Consumer or Space) in a classroom. Denormalizes display data for fast list rendering.

**Table**: `course_classroom_members`

| Column | Type | Key | Description |
|---|---|---|---|
| `classroom_uid` | UUID | Partition key | Groups all members of one classroom |
| `member_id` | UUID | Clustering key ASC | References `Consumer.uid` or `Space.uid` |
| `member_type` | Text | — | `consumer` \| `space` |
| `member_name` | Text | — | Cached display name at join time |
| `member_avatar` | Text | — | Cached avatar URL at join time |
| `role` | Text | — | `teacher` \| `student` |
| `joined_at` | DateTime | — | Membership creation timestamp |
| `is_deleted` | Boolean | — | Soft delete flag |

**Design Note**: `member_name` and `member_avatar` are **denormalized** — copied from the account at join time. They are not updated if the user changes their profile. This is an intentional trade-off: fast member list queries without cross-table joins, at the cost of potentially stale display data.
