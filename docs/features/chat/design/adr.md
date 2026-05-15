# Chat Module — Architecture Decision Records (ADR)

---

## ADR-CHT-001: Partition Messages by `conversation_uid`

**Status**: Accepted
**Date**: v1.0

### Context
The dominant query pattern for messages is "fetch the last N messages in a conversation." Cassandra requires that all rows in a query share the same partition key. Partitioning by `conversation_uid` places all messages of a conversation together, making history queries a single partition scan.

### Decision
`conversation_uid` is the partition key on `chat_messages`. `uid` (UUID v7) is the clustering key in DESC order, so the most recent messages appear first without additional sorting.

### Alternatives Considered
1. **Partition by `sender_id`** — Optimizes "messages by user" but makes "messages in conversation" a scatter-gather.
2. **Partition by time bucket** — Avoids hot partitions for very active conversations but complicates pagination.
3. **Partition by `conversation_uid` (chosen)** — Matches the primary query pattern; acceptable partition size for LMS-scale conversations.

### Consequences
- **Positive**: History query is a single partition scan — O(1) in terms of Cassandra round trips.
- **Negative**: Very high-volume conversations become large partitions over time; a time-bucketing strategy may be needed at scale (e.g., `(conversation_uid, month_bucket)`).

---

## ADR-CHT-002: Sorted UIDs for Direct Conversation Uniqueness

**Status**: Accepted
**Date**: v1.0

### Context
Direct conversations between User A and User B must be unique — creating the conversation twice should return the same record. Without a deduplication strategy, two conversations could exist for the same pair.

### Decision
When creating or looking up a direct conversation, the two UIDs are sorted lexicographically. The smaller UUID is stored as `direct_a_id` and the larger as `direct_b_id`. Both fields are indexed. Lookup always queries both fields with the correctly sorted values.

### Alternatives Considered
1. **Check for existing conversation at service layer before creating** — Two separate queries; race condition risk under concurrent requests.
2. **Composite natural key** — Cassandra does not support unique constraints outside of primary key.
3. **Sorted UID pair (chosen)** — Deterministic; lookup is always the same query regardless of initiator.

### Consequences
- **Positive**: No duplicate direct conversations possible for any user pair.
- **Positive**: Lookup is deterministic — same query regardless of who initiates.
- **Negative**: Client and service must always sort UIDs before any direct conversation operation; easy to miss.

---

## ADR-CHT-003: InMemoryChannelLayer for WebSocket (Development)

**Status**: Accepted (with known limitation)
**Date**: v1.0

### Context
Django Channels requires a channel layer to broadcast messages to multiple connected clients. The simplest option is `InMemoryChannelLayer`, which requires no external infrastructure.

### Decision
Use `InMemoryChannelLayer` for the current development phase. This is explicitly noted as a limitation: it only works for single-process deployments. Multi-instance production deployments must switch to `RedisChannelLayer`.

### Consequences
- **Positive**: Zero external dependencies for local development.
- **Negative**: Does not work across multiple Django processes — messages only broadcast to clients on the same process. Must be replaced with `RedisChannelLayer` before any multi-instance deployment.
