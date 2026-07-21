# Classroom Module — Entities

---

## 1. Classroom

**Purpose**: Represents a learning room owned by a teacher. All content (exams, announcements) belongs to a classroom. Can be **free** or **paid** (MoMo checkout). Paid classrooms gate folder access until a successful MoMo IPN auto-approves the student — only the special `Preview` folder is visible to non-paid consumers.

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
| `pricing_type` | Text | Indexed | `free` (default) \| `paid` |
| `price_vnd` | BigInt | — | Price in VND; must be `≥ 1000` if `pricing_type='paid'` |
| `created_at` | DateTime | — | |
| `updated_at` | DateTime | — | |
| `is_deleted` | Boolean | — | Soft delete flag |
| `deleted_at` | DateTime | — | |

**Computed Property**:
- `resolve_link` (`@cached_property`) — Returns the associated sharing link from the Sharing module, or `None`.
- `preview_folder_uid` (`getter` on response serializer) — Returns the UID of the `ResourceFolder` with `is_preview_only=True`, or `None`.
- `is_paid_classroom` (`getter`) — `True` when `pricing_type='paid'`.

**Auto-created resource**: a `ResourceFolder` with `is_preview_only=True` and name `Preview` is created by `ClassroomService.create_classroom` so that every classroom has a default free tab where the teacher can upload materials visible to everyone.

---

## 2. ClassroomMember

**Purpose**: Records the membership of a user (Consumer or Space) in a classroom. Denormalizes display data for fast list rendering. Tracks payment state for paid classrooms.

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
| `status` | Text | — | `pending` \| `approved` (default `approved` for free auto-join) |
| `is_verified` | Boolean | — | KYC flag |
| `verified_at` | DateTime | — | |
| `has_paid` | Boolean | Indexed | `True` after a successful MoMo IPN (or auto-`True` for free classrooms on join) |
| `paid_at` | DateTime | — | When payment was confirmed |
| `is_deleted` | Boolean | — | Soft delete flag |

**Design Note**: `member_name` and `member_avatar` are **denormalized** — copied from the account at join time. They are not updated if the user changes their profile. This is an intentional trade-off: fast member list queries without cross-table joins, at the cost of potentially stale display data.

**Status lifecycle**:
- Free classroom join → `status='approved'`, `has_paid=True` immediately.
- Paid classroom join via MoMo IPN → `status='approved'`, `has_paid=True`, `paid_at=now()`.
- Manual join on a paid classroom (legacy path) → `status='pending'` (teacher still has to approve; `has_paid` is `False` until then).

---

## 3. ResourceFolder (preview folder)

**Purpose**: Folder hierarchy for classroom documents. Supports a special `is_preview_only` flag used to mark the default free tab of a paid classroom — only one preview folder per classroom. The teacher uploads the free lesson materials into this folder; non-paid consumers can only see its contents.

**Table**: `resource_folders`

| Column | Type | Key | Description |
|---|---|---|---|
| `classroom_id` | UUID | Partition key | Owning classroom |
| `uid` | UUID v7 | Clustering key DESC | Folder id |
| `name` | Text | — | Display name |
| `parent_folder_id` | UUID | — | Parent folder (nullable; root folders have `null`) |
| `owner_id` | UUID | Indexed | Teacher UID |
| `order_index` | Integer | — | Display order |
| `color` | Text | — | UI accent color |
| `is_preview_only` | Boolean | Indexed | Marks the preview folder. At most one per classroom (enforced by `ResourceFolderService.create_folder` and `update_folder`). |

**Invariants**:
- A classroom may have zero or one folder with `is_preview_only=True`. Setting a second one returns 400.
- Removing the flag from the only preview folder is allowed; the next request from the consumer simply shows no preview folder.
- A free classroom still auto-creates a `Preview` folder on creation so that the UI is consistent. The folder is visible to everyone but does not gate any access.

---

## 4. Gating rules

The classroom does not link to a Course. Free vs. paid content is expressed entirely through folders and their `is_preview_only` flag:

- Free classroom → all folders and docs are visible to members.
- Paid classroom + paid member → all folders and docs are visible.
- Paid classroom + non-paid member (or anonymous) → only the `Preview` folder and its docs are returned by `ClassroomDocService.list_tree`. Other folders are hidden, and any `preview-folder` endpoint or paid-aware read endpoint returns only the preview subset.
