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
