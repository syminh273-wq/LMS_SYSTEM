# Classroom Module — Requirements Traceability Matrix (RTM)

| BR ID | BR Description | UR ID | UR Description | FR / NFR ID | FR / NFR Description | Test Case ID | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|---|---|
| BR-CLS-01 | Classroom owned by one Space | UR-CLS-01 | Teacher creates classroom | FR-CLS-01 | account_classrooms table with teacher_id | TC-CLS-001 | Classroom created; teacher_id set to Space uid | v1.0 |
| BR-CLS-01 | Classroom owned by one Space | UR-CLS-01 | Teacher creates classroom | FR-CLS-03 | teacher_id indexed | TC-CLS-002 | Teacher list returns only own classrooms | v1.0 |
| BR-CLS-01 | Classroom owned by one Space | UR-CLS-04 | Teacher removes student | NFR-CLS-02 | Ownership validated without extra DB query | TC-CLS-003 | Non-owner DELETE returns 403; owner DELETE succeeds | v1.0 |
| BR-CLS-02 | Students must join before accessing content | UR-CLS-02 | Teacher adds student | FR-CLS-02 | course_classroom_members table | TC-CLS-004 | Member record created; student appears in member list | v1.0 |
| BR-CLS-02 | Students must join before accessing content | UR-CLS-05 | Student lists classrooms | FR-CLS-04 | Cached member_name and member_avatar | TC-CLS-005 | Member list includes display name and avatar without secondary lookup | v1.0 |
| BR-CLS-02 | Students must join before accessing content | UR-CLS-05 | Student lists classrooms | NFR-CLS-01 | Member list under 300ms | TC-CLS-006 | 500-member classroom list returns in p95 ≤ 300ms | v1.0 |
| BR-CLS-03 | Shareable invite links | UR-CLS-03 | Teacher generates invite link | FR-CLS-05 | resolve_link cached property | TC-CLS-007 | Classroom detail includes sharing_link field if link exists | v1.0 |
| BR-CLS-03 | Shareable invite links | UR-CLS-03 | Teacher generates invite link | — | Join via link workflow | TC-CLS-008 | Student accesses link; ClassroomMember created; used_count incremented | v1.0 |
| BR-CLS-04 | Student cap | UR-CLS-02 | Teacher adds student | FR-CLS-02 | member_count check | TC-CLS-009 | Adding member to at-capacity classroom returns 400 | v1.0 |
| BR-CLS-05 | Soft delete | — | — | FR-CLS-01 | Soft delete on classroom | TC-CLS-010 | Deleted classroom has is_deleted=True; not returned in list or detail queries | v1.0 |

---

## Coverage Summary

| Requirement Type | Total | Covered |
|---|---|---|
| BR | 5 | 5 |
| UR | 5 | 5 |
| FR | 5 | 5 |
| NFR | 2 | 2 |
| **Total** | **17** | **17** |
