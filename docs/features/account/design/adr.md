# Account Module — Architecture Decision Records (ADR)

---

## ADR-ACC-001: Two Separate Models Instead of a Single User Table

**Status**: Accepted
**Date**: v1.0

### Context
The platform serves two user groups with distinct data requirements: Space (teachers) need branding fields like `name`, `slug`, `logo_url`, and `cover_url`; Consumer (students) need a `role` field and `username`. Combining them into a single table would result in many nullable columns and make permission logic more complex.

### Decision
Two separate Cassandra models — `Consumer` and `Space` — each with their own table and field set. Both inherit from a shared `AbstractAuthModel` for common authentication fields.

### Alternatives Considered
1. **Single user table with a type discriminator** — Simpler but creates a wide table with irrelevant nullable columns per user type; permission logic is harder to reason about.
2. **Completely separate, unrelated models** — Maximum isolation but duplicates authentication logic (password hashing, token generation).
3. **Separate models with shared abstract base (chosen)** — Clean separation of concerns, no duplicated auth logic, each table stays lean.

### Consequences
- **Positive**: Each table contains only relevant fields; no nullable columns from the other type.
- **Positive**: Auth logic is defined once in `AbstractAuthModel`.
- **Negative**: The JWT authentication backend must check both tables to resolve a token — a small overhead on every request.

---

## ADR-ACC-002: CassandraJWTAuthentication for Token Resolution

**Status**: Accepted
**Date**: v1.0

### Context
Standard DRF JWT authentication assumes a Django ORM User model. The LMS uses Cassandra with two separate account tables. A custom authentication backend is needed to bridge DRF's expectations with the Cassandra data layer.

### Decision
A custom `CassandraJWTAuthentication` class decodes the JWT token, extracts the `user_id` claim, and performs a lookup against both `Consumer` and `Space` tables. The first match is returned as the authenticated user. If neither table contains the uid, a 401 is returned.

### Alternatives Considered
1. **Use Django's default User model alongside Cassandra** — Creates a dual-database complexity and synchronization burden.
2. **Encode user type in the JWT claims** — Reduces lookup from two queries to one, but couples the token format to the user type classification.
3. **Single lookup with type claim in token** — Considered for v2; adds a `user_type` claim to avoid the second table lookup when the first fails.

### Consequences
- **Positive**: Fully Cassandra-native; no Django ORM User model needed.
- **Negative**: Worst-case requires two Cassandra reads per request (Consumer lookup, then Space lookup). Mitigated by Cassandra's fast primary key lookups.

---

## ADR-ACC-003: Soft Delete Instead of Hard Delete

**Status**: Accepted
**Date**: v1.0

### Context
Cassandra does not support cascading deletes. Permanently removing a user record while maintaining referential integrity across classrooms, messages, and resources would require manual cleanup across multiple tables — a complex and error-prone operation.

### Decision
All account deletions use soft delete: `is_deleted = True` and `deleted_at = now()`. Records are never physically removed. Active queries always filter on `is_deleted = False` (or handle it at the service layer).

### Alternatives Considered
1. **Hard delete with manual cascade** — High complexity, risk of orphaned records in ClassroomMember, Message, Resource tables.
2. **Hard delete with event-driven cascade** — Better but adds infrastructure complexity (message queue required).
3. **Soft delete (chosen)** — Simple, safe, reversible, and audit-friendly.

### Consequences
- **Positive**: No risk of orphaned data in related tables.
- **Positive**: Accounts can be restored if deleted by mistake.
- **Negative**: Deleted records accumulate in Cassandra; periodic TTL cleanup may be needed at scale.
- **Negative**: Every query must be careful to filter on `is_deleted`; missing this filter exposes deleted records.
