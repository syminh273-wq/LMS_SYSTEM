# Chat Module — Requirements Traceability Matrix (RTM)

| BR ID | BR Description | UR ID | UR Description | FR / NFR ID | FR / NFR Description | Test Case ID | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|---|---|
| BR-CHT-01 | Classroom channel created with classroom | — | — | FR-CHT-01 | chat_conversations table | TC-CHT-001 | Classroom creation → Conversation with type=channel and classroom_uid created | v1.0 |
| BR-CHT-02 | One direct conversation per pair | UR-CHT-05 | User starts DM | FR-CHT-03 | Sorted UIDs for direct conversations | TC-CHT-002 | Two users initiate DM; same conversation returned on second attempt | v1.0 |
| BR-CHT-03 | Real-time delivery via WebSocket | UR-CHT-01 | User sends text message | FR-CHT-05 | Django Channels routing | TC-CHT-003 | Message sent via WS appears on second client within 500ms | v1.0 |
| BR-CHT-03 | Real-time delivery via WebSocket | UR-CHT-01 | User sends text message | NFR-CHT-01 | WS delivery under 500ms | TC-CHT-004 | Load test 100 connections; p95 delivery ≤ 500ms | v1.0 |
| BR-CHT-04 | Message history via REST | UR-CHT-03 | User views history | FR-CHT-02 | chat_messages partitioned by conversation_uid | TC-CHT-005 | History endpoint returns messages newest-first; single-partition query | v1.0 |
| BR-CHT-04 | Message history via REST | UR-CHT-03 | User views history | NFR-CHT-02 | Pagination support | TC-CHT-006 | page_size=50 returns correct slice; next page returns subsequent messages | v1.0 |
| BR-CHT-04 | Message history via REST | — | — | FR-CHT-04 | Last message cached on Conversation | TC-CHT-007 | Conversation list response includes last_msg_text without querying messages table | v1.0 |
| BR-CHT-05 | File messages reference Resource | UR-CHT-02 | User sends file | FR-CHT-02 | Message stores resource fields | TC-CHT-008 | File message created; resource_url and resource_name match uploaded Resource | v1.0 |
| — | — | UR-CHT-04 | User deletes message | — | Soft delete workflow | TC-CHT-009 | Deleted message not returned in history; delete broadcast received by all clients | v1.0 |

---

## Coverage Summary

| Requirement Type | Total | Covered |
|---|---|---|
| BR | 5 | 5 |
| UR | 5 | 5 |
| FR | 5 | 5 |
| NFR | 2 | 2 |
| **Total** | **17** | **17** |
