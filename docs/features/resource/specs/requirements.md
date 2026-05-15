# Resource Module — Requirements

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-RES-01 | BR | The platform must provide a centralized file registry so that all modules reference files via a resource record rather than storing file URLs directly. | — | High | All file-attaching modules (Exam, Chat) store `resource_uid`; file URL is resolved from the Resource record. | v1.0 |
| BR-RES-02 | BR | Uploaded files must be stored in Cloudflare R2 with a public URL returned immediately after upload. | — | High | Upload response includes a publicly accessible `url`; file is accessible via that URL without authentication. | v1.0 |
| BR-RES-03 | BR | Resources must be scoped to their uploader — owners can only manage their own files. | — | High | Listing resources returns only records where `owner_id = request.user.uid`. | v1.0 |
| BR-RES-04 | BR | The platform must fall back to local media storage when R2 is not configured (development mode). | — | Medium | If R2 credentials are absent, files are saved to `MEDIA_ROOT` and URLs point to the local media server. | v1.0 |
| UR-RES-01 | UR | As a user, I want to upload a file and receive a URL so that I can attach it to an exam or message. | BR-RES-01 | High | Upload returns `uid`, `url`, `name`, `file_type`, `size`. | v1.0 |
| UR-RES-02 | UR | As a user, I want to list my uploaded files so that I can reuse them. | BR-RES-03 | Medium | List endpoint returns all resources owned by the authenticated user. | v1.0 |
| UR-RES-03 | UR | As a user, I want to delete a file I no longer need. | BR-RES-03 | Low | Soft delete sets `is_deleted = True`; file no longer appears in list. | v1.0 |
| FR-RES-01 | FR | The system shall store resource records in `resource_resources` with `bucket` as partition key and `uid` (UUID v7) as clustering key DESC. | BR-RES-01 | High | Resource queries use bucket + uid for efficient retrieval. | v1.0 |
| FR-RES-02 | FR | The system shall index `owner_id` and `owner_type` to support owner-scoped listing. | BR-RES-03 | High | List query with `owner_id` filter returns results without full-table scan. | v1.0 |
| FR-RES-03 | FR | The system shall upload files to the public R2 bucket by default and return the public CDN URL. | BR-RES-02 | High | Upload response `url` is accessible without authentication headers. | v1.0 |
| FR-RES-04 | FR | The system shall store arbitrary key-value metadata on the resource record via the `metadata` map column. | — | Low | Metadata values are persisted and returned in resource responses. | v1.0 |
| NFR-RES-01 | NFR | Upload endpoint must respond within 3 seconds for files up to 10MB under normal network conditions. | — | High | Upload test with a 10MB file completes in under 3 seconds on a standard connection. | v1.0 |
| NFR-RES-02 | NFR | Deleted resources must not appear in list or detail queries. | BR-RES-03 | High | List and detail endpoints filter `is_deleted = False`. | v1.0 |
