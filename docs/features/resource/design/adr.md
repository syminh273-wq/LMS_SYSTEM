# Resource Module — Architecture Decision Records (ADR)

---

## ADR-RES-001: Central Resource Registry Instead of Inline File URLs

**Status**: Accepted
**Date**: v1.0

### Context
Multiple modules (Exam, Chat, Submission) need to attach files. Without a central registry, each module would manage its own upload logic and store raw URLs directly. This leads to duplicated upload code, no audit trail, and no way to track file usage or perform cleanup.

### Decision
All file uploads go through the Resource module. Other modules reference files by `resource_uid`. The Resource record holds the authoritative URL and metadata.

### Alternatives Considered
1. **Each module uploads independently** — Simpler per-module but duplicates storage logic, no central audit trail.
2. **Central resource table (chosen)** — Single upload path, reuse without re-upload, clear ownership.

### Consequences
- **Positive**: Upload logic written and maintained once.
- **Positive**: Resources can be reused across modules without re-uploading.
- **Negative**: Modules that need to display files must either look up the resource or cache the URL on their own record (Chat and Exam choose to cache).

---

## ADR-RES-002: Cache File URL and Name on Consuming Records

**Status**: Accepted
**Date**: v1.0

### Context
When Chat messages or Exams reference a resource, they need to display the filename and URL. Fetching the Resource record on every render adds a Cassandra read per item.

### Decision
Consuming records (Message, Exam) cache `resource_url` and `resource_name` at creation time, alongside `resource_uid`. The cached values are used for display; the uid is available if the full resource record is needed.

### Consequences
- **Positive**: Zero extra reads to display file messages or exam file info.
- **Negative**: If the resource URL changes (e.g., bucket migration), cached URLs in Message and Exam records become stale. Accepted trade-off.

---

## ADR-RES-003: Dual R2 Bucket Strategy

**Status**: Accepted
**Date**: v1.0

### Context
Some files (profile images, shared exam PDFs) should be publicly accessible via CDN. Others (private submissions, sensitive materials) should not be publicly accessible without authorization.

### Decision
Two R2 buckets: `R2_BUCKET_NAME_PUBLIC` for publicly accessible files and `R2_BUCKET_NAME_PRIVATE` for files requiring signed access. The upload endpoint defaults to the public bucket; callers can specify `is_public=False` for private uploads.

### Consequences
- **Positive**: Public files are served via CDN without authentication overhead.
- **Positive**: Private files are protected at the storage layer.
- **Negative**: Two buckets to configure and monitor; URL generation differs between the two.
