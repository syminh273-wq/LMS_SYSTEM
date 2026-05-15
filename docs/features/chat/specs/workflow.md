# Chat Module — Workflows

---

## 1. Send Text Message via WebSocket

### Actors
- **User** (Consumer or Space)
- **Platform** (Django Channels)
- **Other connected participants**

### Preconditions
- User is authenticated and connected to the WebSocket for the conversation.
- User is a member of the conversation.

### Steps
1. Client sends WebSocket frame: `{ "type": "message.send", "content": "Hello", "msg_type": "text" }`.
2. `MessageConsumer` receives the frame.
3. Consumer validates the user's membership in the conversation.
4. Platform creates a `Message` record in `chat_messages`.
5. Platform updates `last_msg_at`, `last_msg_text`, `last_msg_sender` on the `Conversation` record.
6. Platform broadcasts the message to all participants in the channel group: `{ "type": "message.new", "message": { ... } }`.
7. All connected clients receive the broadcast.

### Edge Cases
- **User not a member**: WebSocket message rejected with an error frame.
- **Client disconnected during broadcast**: Message is persisted; client retrieves it via REST history on reconnect.

---

## 2. Send File Message

### Actors
- **User**
- **Platform**

### Preconditions
- User has already uploaded the file via `POST /api/v1/resource/upload/` and received a `resource_uid`.

### Steps
1. Client sends WebSocket frame: `{ "type": "message.send", "msg_type": "pdf", "resource_uid": "..." }`.
2. Platform fetches the `Resource` record by `resource_uid`.
3. Platform validates the resource exists and belongs to the sender.
4. Platform creates a `Message` record with `resource_uid`, `resource_url`, `resource_name`, `resource_size` cached from the resource.
5. Message is broadcast to all participants.

### Edge Cases
- **Resource not found**: Frame rejected with error.

---

## 3. Load Message History

### Actors
- **User**
- **Platform**

### Steps
1. User sends GET to `/api/v1/consumer/chat/conversations/<uid>/messages/`.
2. Platform queries `chat_messages` where `conversation_uid = uid` and `is_deleted = False`.
3. Results are returned in reverse chronological order (newest first via `uid DESC` clustering).
4. Pagination is applied.

---

## 4. Create Direct Conversation

### Actors
- **User A**
- **Platform**

### Preconditions
- User A is authenticated.
- User B's uid is known.

### Steps
1. User A submits POST with `target_uid` (User B's uid).
2. Platform sorts the two UIDs: smaller → `direct_a_id`, larger → `direct_b_id`.
3. Platform queries `chat_conversations` for an existing record matching this pair.
4. **If found**: Returns the existing conversation.
5. **If not found**: Creates a new `Conversation` with `type = direct`.

### Edge Cases
- **User A and B are the same**: Rejected — cannot create a direct conversation with yourself.

---

## 5. Delete Message

### Actors
- **User (message sender)**
- **Platform**

### Steps
1. User sends DELETE or WebSocket frame `{ "type": "message.delete", "uid": "..." }`.
2. Platform verifies the requesting user is the sender of the message.
3. Platform sets `is_deleted = True`.
4. Platform broadcasts `{ "type": "message.deleted", "uid": "..." }` to all participants.
5. Clients remove the message from their UI.

### Edge Cases
- **Not the sender**: Returns 403 / error frame.
