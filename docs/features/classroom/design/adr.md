# Classroom Module — Architecture Decision Records (ADR)

---

## ADR-CLS-001: Partition ClassroomMember by `classroom_uid`

**Status**: Accepted
**Date**: v1.0

### Context
Listing all members of a classroom is a frequent operation. In Cassandra, efficient queries require that all rows being fetched share the same partition key. Two query patterns are needed: (1) all members of a classroom, and (2) all classrooms a specific member belongs to.

### Decision
`ClassroomMember` uses `classroom_uid` as the partition key. This optimizes the "list members of classroom" query — a single partition scan. The "list classrooms for a member" query requires a secondary index on `member_id`.

### Alternatives Considered
1. **Partition by `member_id`** — Optimizes the student's classroom list but makes the member list query a scatter-gather across all partitions.
2. **Two tables (one per query pattern)** — Optimal for both queries but doubles write complexity and risk of inconsistency.
3. **Partition by `classroom_uid` with secondary index on `member_id` (chosen)** — Single table, efficient primary query pattern, secondary index for the less frequent pattern.

### Consequences
- **Positive**: Member list for a classroom is a fast single-partition read.
- **Negative**: Listing classrooms by member_id uses a secondary index — acceptable for Cassandra's secondary index limitations given the expected query frequency.

---

## ADR-CLS-002: Denormalize `member_name` and `member_avatar` on ClassroomMember

**Status**: Accepted
**Date**: v1.0

### Context
The member list endpoint must return display name and avatar for each member. In a relational database, this would be a JOIN. Cassandra does not support joins — cross-table lookups require N+1 queries (one per member) or application-level batching.

### Decision
At join time, `member_name` and `member_avatar` are copied from the account record onto the `ClassroomMember` row. Member list queries are then satisfied with a single partition scan and no secondary lookups.

### Alternatives Considered
1. **N+1 lookups per member list** — Simple but O(n) reads per request; unacceptable at scale.
2. **Batch fetch by uid list** — Better, but still requires a second round trip to Cassandra.
3. **Denormalize at write time (chosen)** — Zero secondary reads for member lists; display data may become stale if the user updates their profile.

### Consequences
- **Positive**: Member list queries are O(1) in terms of round trips — single partition scan.
- **Negative**: If a user updates their display name or avatar, existing membership records reflect the old values. This is accepted as a product trade-off for the LMS use case.

---

## ADR-CLS-003: Lazy Sharing Link via `resolve_link` Cached Property

**Status**: Accepted
**Date**: v1.0

### Context
Classroom detail responses should include the invite link without requiring the client to make a separate API call to the Sharing module. However, many classrooms may not have a sharing link, and fetching the link on every classroom query would add unnecessary overhead.

### Decision
`Classroom.resolve_link` is implemented as a `@cached_property`. It is only fetched when the property is accessed — i.e., when serializing a classroom detail response that includes the link field. It is not fetched for list views.

### Alternatives Considered
1. **Always fetch sharing link in ClassroomService** — Adds a Cassandra read to every classroom fetch, even for list views where the link is not shown.
2. **Separate API endpoint for the link** — Requires two client requests; worse UX.
3. **Cached property (chosen)** — Lazy, zero overhead for views that don't access it.

### Consequences
- **Positive**: No extra reads for views that don't need the link.
- **Positive**: Client gets the link in one request for detail views.
- **Negative**: `@cached_property` on a Cassandra model is instance-scoped; the result is not shared across requests or instances.
