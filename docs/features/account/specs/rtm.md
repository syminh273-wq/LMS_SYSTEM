# Account Module — Requirements Traceability Matrix (RTM)

| BR ID | BR Description | UR ID | UR Description | FR / NFR ID | FR / NFR Description | Test Case ID | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|---|---|
| BR-ACC-01 | Support two distinct account types | UR-ACC-01 | Teacher registers Space account | FR-ACC-01 | AbstractAuthModel base | TC-ACC-001 | Space created; password hashed; JWT returned | v1.0 |
| BR-ACC-01 | Support two distinct account types | UR-ACC-02 | Teacher logs in | FR-ACC-04 | JWT issued on login | TC-ACC-002 | Login returns access + refresh tokens; tokens decode to correct Space uid | v1.0 |
| BR-ACC-01 | Support two distinct account types | UR-ACC-04 | Student registers Consumer account | FR-ACC-02 | Consumer stored in account_consumers | TC-ACC-003 | Consumer created; role defaults to student; JWT returned | v1.0 |
| BR-ACC-01 | Support two distinct account types | UR-ACC-05 | Student logs in | FR-ACC-05 | CassandraJWTAuthentication resolves user type | TC-ACC-004 | Consumer login returns valid JWT; auth middleware resolves to Consumer | v1.0 |
| BR-ACC-01 | Support two distinct account types | — | — | FR-ACC-06 | Email and username indexed | TC-ACC-005 | Lookup by email returns correct record without full-table scan | v1.0 |
| BR-ACC-02 | Space branding fields | UR-ACC-03 | Teacher updates Space profile | FR-ACC-03 | Space stored with slug unique index | TC-ACC-006 | Profile update persisted; slug uniqueness enforced; duplicate slug rejected | v1.0 |
| BR-ACC-03 | Consumer role classification | UR-ACC-06 | Student updates profile | FR-ACC-02 | Consumer model with role field | TC-ACC-007 | Consumer role defaults to student on creation; role field accepts valid values | v1.0 |
| BR-ACC-04 | Enforce identity verification | — | — | FR-ACC-04 | JWT tokens issued on login | TC-ACC-008 | Protected endpoints reject requests without valid JWT; 401 returned | v1.0 |
| BR-ACC-04 | Enforce identity verification | — | — | NFR-ACC-01 | Passwords hashed securely | TC-ACC-009 | DB inspection shows no plaintext passwords; hash validates against input | v1.0 |
| BR-ACC-05 | Soft-delete pattern | — | — | FR-ACC-02 | Consumer soft delete | TC-ACC-010 | Deleted Consumer has is_deleted=True and deleted_at set; not returned in active queries | v1.0 |
| BR-ACC-05 | Soft-delete pattern | — | — | FR-ACC-03 | Space soft delete | TC-ACC-011 | Deleted Space has is_deleted=True; JWT for deleted Space returns 401 | v1.0 |
| — | — | — | — | NFR-ACC-02 | Auth responds within 500ms p95 | TC-ACC-012 | Load test 500 concurrent users; p95 latency ≤ 500ms | v1.0 |
| — | — | — | — | NFR-ACC-03 | Deleted accounts excluded from queries | TC-ACC-013 | List endpoints return only active accounts; deleted records never appear | v1.0 |

---

## Coverage Summary

| Requirement Type | Total | Covered |
|---|---|---|
| BR | 5 | 5 |
| UR | 6 | 6 |
| FR | 6 | 6 |
| NFR | 3 | 3 |
| **Total** | **20** | **20** |
