# Chat Module — Requirements

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CHT-01 | BR | Every classroom must have a dedicated group chat channel automatically created with the classroom. | — | High | Classroom creation triggers Conversation creation with `type=channel` and `classroom_uid` set. | v1.0 |
| BR-CHT-02 | BR | Any two users must be able to start a direct message conversation, with at most one conversation per pair. | — | High | Two users attempting to create a direct conversation twice results in the same conversation being returned. | v1.0 |
| BR-CHT-03 | BR | Messages must be delivered in real time to all connected participants via WebSocket. | — | High | Message sent via WebSocket appears on all connected clients within 500ms. | v1.0 |
| BR-CHT-04 | BR | Message history must be retrievable via REST API, paginated and ordered newest first. | — | High | GET messages endpoint returns paginated results; each page is ordered by `uid DESC`. | v1.0 |
| BR-CHT-05 | BR | File messages must reference a previously uploaded Resource record. | — | Medium | Message with `msg_type != text` requires `resource_uid`; resource must exist. | v1.0 |
| UR-CHT-01 | UR | As a user, I want to send a text message in a classroom chat so that I can communicate with participants. | BR-CHT-03 | High | Message sent via WebSocket is received by all other connected participants. | v1.0 |
| UR-CHT-02 | UR | As a user, I want to send a file in a chat so that I can share documents and media. | BR-CHT-05 | Medium | File message created with resource_uid; resource_url and resource_name cached on message. | v1.0 |
| UR-CHT-03 | UR | As a user, I want to view message history so that I can catch up on missed messages. | BR-CHT-04 | High | History endpoint returns messages in reverse chronological order with pagination. | v1.0 |
| UR-CHT-04 | UR | As a user, I want to delete a message I sent so that I can correct mistakes. | — | Medium | Soft delete sets is_deleted=True; message no longer appears in history for other users. | v1.0 |
| UR-CHT-05 | UR | As a user, I want to start a direct message conversation with another user. | BR-CHT-02 | Medium | Direct conversation created or retrieved for the user pair; no duplicate conversations. | v1.0 |
| FR-CHT-01 | FR | The system shall store conversations in `chat_conversations` partitioned by `bucket` with `uid` clustering DESC. | BR-CHT-01 | High | Conversation queries use bucket + uid for retrieval. | v1.0 |
| FR-CHT-02 | FR | The system shall store messages in `chat_messages` partitioned by `conversation_uid` with `uid` clustering DESC. | BR-CHT-04 | High | All messages of a conversation are co-located; list query is a single-partition scan. | v1.0 |
| FR-CHT-03 | FR | The system shall enforce unique direct conversations using sorted UIDs: `direct_a_id` (smaller) and `direct_b_id` (larger). | BR-CHT-02 | High | Looking up a direct conversation by the pair always returns the same record regardless of which user initiates. | v1.0 |
| FR-CHT-04 | FR | The system shall cache `last_msg_at`, `last_msg_text`, and `last_msg_sender` on the Conversation record for efficient conversation list rendering. | BR-CHT-04 | Medium | Conversation list response includes last message preview without querying chat_messages. | v1.0 |
| FR-CHT-05 | FR | The system shall route WebSocket connections to the correct Conversation channel group using Django Channels. | BR-CHT-03 | High | Two clients connected to the same conversation_uid both receive the same broadcast message. | v1.0 |
| NFR-CHT-01 | NFR | WebSocket message delivery must complete within 500ms end-to-end under normal load. | BR-CHT-03 | High | Load test with 100 concurrent connections; p95 delivery latency ≤ 500ms. | v1.0 |
| NFR-CHT-02 | NFR | Message history must support pagination with at least 50 messages per page. | BR-CHT-04 | Medium | History endpoint accepts `page` and `page_size` params; returns correct slice. | v1.0 |
