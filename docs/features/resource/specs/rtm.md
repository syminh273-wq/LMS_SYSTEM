# Resource Module — Requirements Traceability Matrix (RTM)

| BR ID | BR Description | UR ID | UR Description | FR / NFR ID | FR / NFR Description | Test Case ID | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|---|---|
| BR-RES-01 | Centralized file registry | UR-RES-01 | User uploads file | FR-RES-01 | resource_resources table | TC-RES-001 | Upload creates Resource record with uid, url, name, file_type, size | v1.0 |
| BR-RES-02 | Files stored in R2 with public URL | UR-RES-01 | User uploads file | FR-RES-03 | Upload to public R2 bucket | TC-RES-002 | Returned URL is publicly accessible without auth headers | v1.0 |
| BR-RES-02 | Files stored in R2 with public URL | — | — | NFR-RES-01 | Upload within 3s for 10MB | TC-RES-003 | 10MB file upload completes in under 3 seconds | v1.0 |
| BR-RES-03 | Owner-scoped access | UR-RES-02 | User lists own files | FR-RES-02 | owner_id and owner_type indexed | TC-RES-004 | List returns only resources where owner_id matches authenticated user | v1.0 |
| BR-RES-03 | Owner-scoped access | UR-RES-03 | User deletes file | NFR-RES-02 | Deleted resources excluded | TC-RES-005 | Deleted resource not returned in list or detail; is_deleted=True in DB | v1.0 |
| BR-RES-04 | Local fallback in development | — | — | FR-RES-03 | StorageService local fallback | TC-RES-006 | With no R2 credentials, upload saves to MEDIA_ROOT; URL uses MEDIA_URL | v1.0 |
| — | — | — | — | FR-RES-04 | Metadata map column | TC-RES-007 | Metadata key-value pairs persisted and returned in resource response | v1.0 |

---

## Coverage Summary

| Requirement Type | Total | Covered |
|---|---|---|
| BR | 4 | 4 |
| UR | 3 | 3 |
| FR | 4 | 4 |
| NFR | 2 | 2 |
| **Total** | **13** | **13** |
