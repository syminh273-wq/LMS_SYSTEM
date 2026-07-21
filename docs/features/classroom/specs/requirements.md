# Classroom Module — Requirements

## Requirement Types

- **BR** — Business Requirement
- **UR** — User Requirement
- **FR** — Functional Requirement
- **NFR** — Non-Functional Requirement

---

## Requirements Table

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-01 | BR | A classroom must be owned by exactly one Space account. Only the owner can create, update, or delete the classroom. | — | High | Requests to modify a classroom by a non-owner return 403. | v1.0 |
| BR-CLS-02 | BR | Students must join a classroom before they can access its content. | — | High | Consumer cannot access classroom content without a ClassroomMember record. | v1.0 |
| BR-CLS-03 | BR | Classrooms must support shareable invite links so teachers can onboard students without manual entry. | — | Medium | A sharing link created for a classroom adds the user as a member when accessed. | v1.0 |
| BR-CLS-04 | BR | A classroom must support a maximum student cap, with `0` meaning unlimited. | BR-CLS-01 | Low | Creating a membership when `member_count >= max_students` (and `max_students > 0`) is rejected. | v1.0 |
| BR-CLS-05 | BR | Classroom deletion must follow a soft-delete pattern. | — | High | Deleted classrooms are hidden from queries; data is retained in Cassandra. | v1.0 |
| UR-CLS-01 | UR | As a teacher, I want to create a classroom so that I can organize my students and content. | BR-CLS-01 | High | POST to classroom endpoint creates a record; teacher becomes the owner. | v1.0 |
| UR-CLS-02 | UR | As a teacher, I want to add students to my classroom so that they can access content. | BR-CLS-02 | High | Teacher adds Consumer by uid; ClassroomMember record created with role=student. | v1.0 |
| UR-CLS-03 | UR | As a teacher, I want to generate an invite link for my classroom so that students can join without manual addition. | BR-CLS-03 | Medium | Sharing link created for classroom; accessing link adds the user as a member. | v1.0 |
| UR-CLS-04 | UR | As a teacher, I want to remove a student from my classroom so that I can manage access. | BR-CLS-01 | Medium | Member record soft-deleted; student no longer appears in member list. | v1.0 |
| UR-CLS-05 | UR | As a student, I want to see all classrooms I have joined so that I can navigate to my content. | BR-CLS-02 | High | Consumer list endpoint returns all classrooms where a ClassroomMember record exists for that Consumer. | v1.0 |
| FR-CLS-01 | FR | The system shall store classrooms in the `account_classrooms` table with `bucket` as partition key and `uid` (UUID v7) as clustering key DESC. | BR-CLS-01 | High | Classroom queries use bucket + uid for efficient retrieval. | v1.0 |
| FR-CLS-02 | FR | The system shall store classroom members in `course_classroom_members` with `classroom_uid` as partition key and `member_id` as clustering key ASC. | BR-CLS-02 | High | Member list for a classroom is retrieved with a single partition scan. | v1.0 |
| FR-CLS-03 | FR | The system shall index `teacher_id` on the classroom table to support teacher-scoped classroom listing. | BR-CLS-01 | High | Teacher list endpoint returns only classrooms where `teacher_id = space.uid`. | v1.0 |
| FR-CLS-04 | FR | The system shall cache `member_name` and `member_avatar` on the ClassroomMember record at join time. | BR-CLS-02 | Medium | Member list response includes display name and avatar without secondary lookups. | v1.0 |
| FR-CLS-05 | FR | The system shall expose a `resolve_link` cached property on Classroom that returns the associated sharing link if one exists. | BR-CLS-03 | Medium | Classroom detail response includes `sharing_link` field populated from the Sharing module. | v1.0 |
| NFR-CLS-01 | NFR | Member list queries must return results in under 300ms for classrooms with up to 500 members. | — | High | Load test with 500-member classroom; p95 latency ≤ 300ms. | v1.0 |
| NFR-CLS-02 | NFR | Classroom ownership must be validated on every write operation without an additional database query. | BR-CLS-01 | High | Ownership check uses `teacher_id` from the classroom record retrieved in the same request. | v1.0 |

### Paid classroom + preview folder (LMS-paid-classroom-preview-folder)

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-06 | BR | A classroom can be free or paid. Paid classrooms require a successful MoMo payment before students can access full content. | — | High | `Classroom.pricing_type ∈ {free, paid}`; `Classroom.price_vnd` ≥ 1000 when paid. | v1.1 |
| BR-CLS-07 | BR | Paid classrooms must surface a Preview folder visible to everyone, including unpaid students and anonymous visitors. | BR-CLS-06 | High | At most one `ResourceFolder.is_preview_only=True` per classroom; auto-created on classroom creation. | v1.1 |
| BR-CLS-08 | BR | Paid classrooms must link to a Course so that lesson gating can reuse `CourseLesson.is_preview`. | BR-CLS-06 | Medium | `Classroom.course_uid` references `Course.uid`. Lessons are read from `course_lessons` and filtered by `is_preview` when the consumer has not paid. | v1.1 |
| BR-CLS-09 | BR | A successful MoMo payment for a paid classroom must immediately auto-approve the student (no teacher approval). | BR-CLS-06 | High | On MoMo IPN with `resource_type='classroom'`, `ClassroomMemberService.approve_paid_member` is invoked and the student gets `status='approved'`, `has_paid=True`. | v1.1 |
| UR-CLS-06 | UR | As a teacher, I want to mark a folder as Preview so that it is the default free content of a paid classroom. | BR-CLS-07 | High | Toggling `is_preview_only` on a folder persists; setting it on a second folder is rejected with 400. | v1.1 |
| UR-CLS-07 | UR | As a student, I want to see all lessons and folders of a paid classroom after I have paid. | BR-CLS-06 | High | After payment + IPN, `ClassroomLessonService.list_lessons` returns all `is_published=True` lessons and `ClassroomDocService.list_tree` returns the full tree. | v1.1 |
| FR-CLS-06 | FR | The system shall add `pricing_type`, `price_vnd`, `course_uid` columns to `account_classrooms` (additive migration via `sync_cassandra`). | BR-CLS-06 | High | `sync_cassandra` shows the new columns on the live keyspace. | v1.1 |
| FR-CLS-07 | FR | The system shall add `has_paid`, `paid_at` columns to `course_classroom_members`. | BR-CLS-09 | High | New columns present in the keyspace after `sync_cassandra`. | v1.1 |
| FR-CLS-08 | FR | The system shall add `is_preview_only` column to `resource_folders` and enforce the at-most-one rule on create and update. | BR-CLS-07 | High | Repository + service refuse to create/update a second preview folder with 400. | v1.1 |
| FR-CLS-09 | FR | The consumer classroom `retrieve` endpoint shall return `requires_payment: true` and `has_paid: false` for paid classrooms where the consumer has not paid. | BR-CLS-06 | High | Consumer can read basic classroom info + preview folder, but lesson and folder listing endpoints return only the preview subset. | v1.1 |
| FR-CLS-10 | FR | The consumer classroom `join` endpoint shall call `PaymentService.initiate(resource_type='classroom')` for paid classrooms and return the MoMo `pay_url`. | BR-CLS-06 | High | Calling `POST /api/v1/consumer/course/classrooms/join/` with a paid classroom pid returns `{requires_payment: true, pay_url, order_id, amount}`. | v1.1 |
| FR-CLS-11 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/{uid}/lessons/` returning `CourseLesson` records filtered by paid status. | BR-CLS-08 | High | Endpoint returns `{lessons, pricing_type, is_locked, is_paid_member}`. | v1.1 |
| FR-CLS-12 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/{uid}/preview-folder/` returning the preview folder and its docs without auth. | BR-CLS-07 | High | Endpoint returns `{folder, docs}` or `{folder: null, docs: []}` if no preview folder exists. | v1.1 |
| FR-CLS-13 | FR | The system shall expose `POST /api/v1/consumer/course/classrooms/{uid}/checkout/` to initiate a MoMo payment for a paid classroom. | BR-CLS-06 | High | Endpoint returns `{classroom_uid, amount, order_id, pay_url}`. | v1.1 |
| FR-CLS-14 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/{uid}/access/` to poll payment status. | BR-CLS-06 | High | Endpoint returns `{has_access, has_paid, pricing_type, is_paid_classroom, pending_payment}`. | v1.1 |
| NFR-CLS-03 | NFR | Lesson/folder listing for paid + unpaid consumers must not degrade beyond 100ms additional latency. | BR-CLS-06 | High | p95 latency of `/lessons/` and `/docs/tree/` for paid classrooms ≤ 350ms (baseline + 100ms). | v1.1 |
