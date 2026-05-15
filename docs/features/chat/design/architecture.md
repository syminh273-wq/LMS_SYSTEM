# Chat Module — Architecture

## Overview

The Chat module has two communication paths: a **REST API** for conversation management and history, and a **WebSocket** layer built on Django Channels for real-time delivery. Both paths share the same Cassandra data layer.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                      Chat Module                            │
│                                                             │
│  REST Path                    WebSocket Path               │
│  ─────────────────────        ──────────────────────────── │
│  ConversationViewSet          MessageConsumer (Channels)   │
│  MessageViewSet               core/ws/consumers/           │
│        │                             │                     │
│        └──────────────┬──────────────┘                     │
│                       │                                     │
│           ┌───────────▼────────────┐                       │
│           │   ConversationService  │                       │
│           │   MessageService       │                       │
│           │   ConversationMember   │                       │
│           │   Service              │                       │
│           └───────────┬────────────┘                       │
│                       │                                     │
│        ┌──────────────┼──────────────┐                     │
│        │              │              │                     │
│  ┌─────▼─────┐ ┌──────▼──────┐ ┌────▼────────────────┐   │
│  │Conversation│ │   Message   │ │ ConversationMember  │   │
│  │ Repository │ │ Repository  │ │ Repository          │   │
│  └─────┬─────┘ └──────┬──────┘ └────┬────────────────┘   │
└────────┼──────────────┼──────────────┼────────────────────┘
         │              │              │
  ┌──────▼──────┐ ┌─────▼───────┐ ┌───▼──────────────┐
  │chat_convers-│ │chat_messages│ │ chat_conversation │
  │ations       │ │             │ │ _members          │
  └─────────────┘ └─────────────┘ └───────────────────┘
```

---

## WebSocket Layer

**Consumer**: `core/ws/consumers/message_consumer.py`
**Routing**: `core/ws/routing.py`
**Auth Middleware**: `core/ws/middleware/jwt_auth_middleware.py`

### Connection lifecycle
1. Client connects: `ws://<host>/ws/chat/<conversation_uid>/`
2. JWT middleware authenticates the connection from the `Authorization` header.
3. Consumer joins the Channels group for this conversation: `chat_<conversation_uid>`.
4. On message receive: validate → persist → broadcast to group.
5. On disconnect: consumer leaves the group.

### Channel Layers
Currently using `InMemoryChannelLayer` (configured in `settings.py`). For production multi-instance deployments, this should be replaced with `RedisChannelLayer`.

---

## Direct Conversation Deduplication

To ensure only one direct conversation exists per user pair, UIDs are sorted before storing:
```python
a, b = sorted([user_a_uid, user_b_uid])
# direct_a_id = a (smaller), direct_b_id = b (larger)
```
This makes the lookup deterministic regardless of which user initiates.
