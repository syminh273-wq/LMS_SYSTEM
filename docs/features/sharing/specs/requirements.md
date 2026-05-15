# Sharing Module — Requirements

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-SHR-01 | BR | The platform must support shareable links for any resource type using a single generic mechanism. | — | High | A link with `resource_type=classroom` and `resource_id` correctly triggers the join-classroom action when accessed. | v1.0 |
| BR-SHR-02 | BR | Links must support optional time-based and usage-count-based expiry. | BR-SHR-01 | Medium | Link with `expired_at` in the past returns 400; link with `used_count >= max_usage` returns 400. | v1.0 |
| BR-SHR-03 | BR | Link access must be idempotent for the same user — accessing the same classroom link twice does not create duplicate memberships. | BR-SHR-01 | Medium | Second access of same link by same user returns success without creating a duplicate ClassroomMember. | v1.0 |
| UR-SHR-01 | UR | As a teacher, I want to create an invite link for my classroom so that students can join without manual entry. | BR-SHR-01 | High | POST to sharing links endpoint with `resource_type=classroom` returns a link with a unique `code`. | v1.0 |
| UR-SHR-02 | UR | As a student, I want to access an invite link so that I am automatically added to the classroom. | BR-SHR-01 | High | GET with valid link code triggers join action; student appears in classroom member list. | v1.0 |
| UR-SHR-03 | UR | As a teacher, I want to set an expiry and usage limit on the link so that I can control who joins. | BR-SHR-02 | Medium | Link with `max_usage=30` stops working after 30 uses; link with `expired_at` stops working after that time. | v1.0 |
| FR-SHR-01 | FR | The system shall store links in `sharing_links` with `uid` (UUID v7) as primary key. | BR-SHR-01 | High | Link CRUD operations target `sharing_links`; uid is returned on creation. | v1.0 |
| FR-SHR-02 | FR | The system shall generate a unique `code` for each link, indexed for fast lookup by code. | BR-SHR-01 | High | Two links never have the same code; lookup by code returns result without full-table scan. | v1.0 |
| FR-SHR-03 | FR | The system shall validate link state (active, not expired, not exhausted) before executing the action. | BR-SHR-02 | High | All three checks run before any side effects; partial failure returns 400 with a clear reason. | v1.0 |
| FR-SHR-04 | FR | The system shall increment `used_count` on every successful link access. | BR-SHR-01 | High | After N successful accesses, `used_count = N` on the link record. | v1.0 |
| NFR-SHR-01 | NFR | Link lookup by `code` must return within 100ms. | — | High | Secondary index on `code` enables sub-100ms lookup under normal Cassandra load. | v1.0 |
