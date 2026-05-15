# Sharing Module — Architecture Decision Records (ADR)

---

## ADR-SHR-001: Generic Link Model with `resource_type` + `action`

**Status**: Accepted
**Date**: v1.0

### Context
Multiple features need shareable links (classrooms, future events, files). Building a separate link model per feature duplicates the short-code generation, expiry, and usage-tracking logic.

### Decision
A single generic `Link` model with `resource_type` (what it links to) and `action` (what happens on access). The `LinkService` routes to the appropriate handler based on `resource_type`.

### Alternatives Considered
1. **One link model per feature** — No shared infrastructure; maximum isolation but lots of duplication.
2. **Generic model with resource_type routing (chosen)** — Write link infrastructure once; extend by adding new handlers.

### Consequences
- **Positive**: New resource types require only a new action handler — no model or API changes.
- **Negative**: Action routing logic in `LinkService` grows as more resource types are added; should be refactored to a registry pattern if it exceeds 5-6 types.

---

## ADR-SHR-002: Short Code as Indexed Secondary Column

**Status**: Accepted
**Date**: v1.0

### Context
Links are shared externally as short URLs (e.g., `/join/abc123`). Users access links by code, not by `uid`. Cassandra's primary key lookup by `uid` cannot serve code-based lookups efficiently without a secondary index.

### Decision
`code` is stored as a secondary indexed column. Link lookup by code uses this index. Code generation uses a short alphanumeric random string (collision probability is negligible at LMS scale).

### Alternatives Considered
1. **Use uid as the code** — UUID is too long for a share URL; poor UX.
2. **Separate lookup table keyed by code** — Eliminates secondary index but adds write complexity (two writes per link creation).
3. **Secondary index on code (chosen)** — Simpler implementation; acceptable performance at LMS scale.

### Consequences
- **Positive**: Simple implementation — one table, one write per link.
- **Negative**: Cassandra secondary indexes have scalability limits; acceptable for LMS-scale usage (thousands, not millions of links).
