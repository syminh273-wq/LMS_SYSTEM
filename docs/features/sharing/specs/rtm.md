# Sharing Module — Requirements Traceability Matrix (RTM)

| BR ID | BR Description | UR ID | UR Description | FR / NFR ID | FR / NFR Description | Test Case ID | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|---|---|
| BR-SHR-01 | Generic resource linking | UR-SHR-01 | Teacher creates invite link | FR-SHR-01 | sharing_links table | TC-SHR-001 | Link created with unique code and resource_type=classroom | v1.0 |
| BR-SHR-01 | Generic resource linking | UR-SHR-01 | Teacher creates invite link | FR-SHR-02 | Unique code indexed | TC-SHR-002 | Two links never share the same code | v1.0 |
| BR-SHR-01 | Generic resource linking | UR-SHR-02 | Student accesses link | FR-SHR-04 | used_count incremented | TC-SHR-003 | After 5 accesses, used_count = 5 on link record | v1.0 |
| BR-SHR-01 | Generic resource linking | UR-SHR-02 | Student accesses link | NFR-SHR-01 | Link lookup under 100ms | TC-SHR-004 | Code lookup returns result in under 100ms | v1.0 |
| BR-SHR-02 | Expiry and usage limits | UR-SHR-03 | Teacher sets expiry/limit | FR-SHR-03 | Validate link state | TC-SHR-005 | Expired link returns 400; exhausted link returns 400 | v1.0 |
| BR-SHR-03 | Idempotent access | UR-SHR-02 | Student accesses link | FR-SHR-03 | Validate before side effects | TC-SHR-006 | Second access by same student adds no duplicate member | v1.0 |

---

## Coverage Summary

| Requirement Type | Total | Covered |
|---|---|---|
| BR | 3 | 3 |
| UR | 3 | 3 |
| FR | 4 | 4 |
| NFR | 1 | 1 |
| **Total** | **11** | **11** |
