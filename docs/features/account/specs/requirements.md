# Account Module — Requirements

## Requirement Types

- **BR** — Business Requirement: What the business needs to achieve
- **UR** — User Requirement: What users need to accomplish
- **FR** — Functional Requirement: Specific system behavior
- **NFR** — Non-Functional Requirement: Quality attributes

---

## Requirements Table

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-ACC-01 | BR | The platform must support two distinct account types: Space (teacher) and Consumer (student), each with separate identity management and access scopes. | — | High | Each account type has its own model, auth flow, and API namespace. | v1.0 |
| BR-ACC-02 | BR | Space accounts must support organizational branding fields to allow teachers to represent an educational brand. | BR-ACC-01 | Medium | Space profile includes `name`, `slug`, `logo_url`, `cover_url`; slug is unique and URL-safe. | v1.0 |
| BR-ACC-03 | BR | Consumer accounts must support role-based classification within the student context. | BR-ACC-01 | Medium | Consumer carries a `role` field with values: `student`, `instructor`, `admin`. | v1.0 |
| BR-ACC-04 | BR | The platform must enforce identity verification before granting access to protected resources. | — | High | Unverified accounts cannot access classroom or content endpoints. | v1.0 |
| BR-ACC-05 | BR | Account deletion must follow a soft-delete pattern to preserve audit history. | — | High | Deleted accounts have `is_deleted = True` and `deleted_at` set; they do not appear in active queries. | v1.0 |
| UR-ACC-01 | UR | As a teacher, I want to register a Space account so that I can create and manage classrooms. | BR-ACC-01 | High | Space registers with email and password; account is created; JWT tokens returned. | v1.0 |
| UR-ACC-02 | UR | As a teacher, I want to log in to my Space account so that I can manage my classrooms and students. | BR-ACC-01 | High | Space logs in with email and password; valid JWT access and refresh tokens returned. | v1.0 |
| UR-ACC-03 | UR | As a teacher, I want to update my Space profile (name, logo, description) so that my brand identity is visible to students. | BR-ACC-02 | Medium | Space updates profile fields; changes persisted and returned on next profile fetch. | v1.0 |
| UR-ACC-04 | UR | As a student, I want to register a Consumer account so that I can join classrooms. | BR-ACC-01 | High | Consumer registers with email and password; account is created; JWT tokens returned. | v1.0 |
| UR-ACC-05 | UR | As a student, I want to log in to my Consumer account so that I can access my classrooms. | BR-ACC-01 | High | Consumer logs in with email and password; valid JWT tokens returned. | v1.0 |
| UR-ACC-06 | UR | As a student, I want to update my profile (name, avatar, phone) so that my identity is complete. | BR-ACC-01 | Medium | Consumer updates profile fields; changes persisted. | v1.0 |
| FR-ACC-01 | FR | The system shall provide an abstract base model (`AbstractAuthModel`) with fields: password, is_verified, is_active, last_login, verified_at. | BR-ACC-01 | High | Both Space and Consumer inherit from `AbstractAuthModel`; password is always stored as a secure hash. | v1.0 |
| FR-ACC-02 | FR | The system shall store Consumer records in the `account_consumers` Cassandra table with `uid` as primary key. | BR-ACC-01 | High | Consumer CRUD operations target the correct table; uid is a UUID generated on creation. | v1.0 |
| FR-ACC-03 | FR | The system shall store Space records in the `account_spaces` Cassandra table with `uid` as primary key and `slug` as a unique indexed field. | BR-ACC-02 | High | Space CRUD operations target the correct table; slug uniqueness is enforced at service level. | v1.0 |
| FR-ACC-04 | FR | The system shall issue JWT access tokens (60 min) and refresh tokens (1 day) upon successful login for both account types. | BR-ACC-01 | High | Login response includes `access` and `refresh` fields; tokens decode to correct user type and uid. | v1.0 |
| FR-ACC-05 | FR | The system shall resolve the JWT token to the correct account type (Space or Consumer) on each authenticated request. | BR-ACC-01 | High | `CassandraJWTAuthentication` correctly identifies user type from token claims; wrong type returns 401. | v1.0 |
| FR-ACC-06 | FR | The system shall index `email` and `username` on Consumer, and `email` and `slug` on Space to support fast lookup. | BR-ACC-01 | High | Queries by email or username on Consumer return results without full-table scan. | v1.0 |
| NFR-ACC-01 | NFR | All passwords must be stored using a secure hashing algorithm. | BR-ACC-04 | Critical | No plaintext passwords are stored; all password fields pass cryptographic validation. | v1.0 |
| NFR-ACC-02 | NFR | Authentication endpoints must respond within 500ms at the 95th percentile under normal load. | — | High | Load test with 500 concurrent users shows p95 ≤ 500ms. | v1.0 |
| NFR-ACC-03 | NFR | Deleted accounts must not appear in any active query results. | BR-ACC-05 | High | Queries on both tables with default filters exclude records where `is_deleted = True`. | v1.0 |
