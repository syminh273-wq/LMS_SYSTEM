# Sharing Module — Architecture

## Overview

The Sharing module is intentionally generic. The `LinkService` handles validation and usage tracking; action execution (e.g., adding a classroom member) is delegated to the appropriate module's service.

---

## Architecture Diagram

```
┌────────────────────────────────────────────┐
│              Sharing Module                 │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │           LinkViewSet                │  │
│  └──────────────────┬───────────────────┘  │
│                     │                       │
│  ┌──────────────────▼───────────────────┐  │
│  │           LinkService                │  │
│  │  - validate (active, expiry, usage)  │  │
│  │  - route by resource_type            │  │
│  │  - increment used_count              │  │
│  └──────┬──────────────────┬────────────┘  │
│         │                  │               │
│  ┌──────▼──────┐   ┌───────▼────────────┐ │
│  │ LinkRepository│ │ Action Handlers     │ │
│  └──────┬──────┘   │ (ClassroomMember    │ │
│         │          │  Service, etc.)     │ │
└─────────┼──────────┴────────────────────┘─┘
          │
  ┌───────▼──────────┐
  │  sharing_links   │
  │  (Cassandra)     │
  └──────────────────┘
```

---

## Action Routing

When a link is accessed, `LinkService` reads `resource_type` and delegates to the appropriate handler:

| `resource_type` | `action` | Handler |
|---|---|---|
| `classroom` | `join` | `ClassroomMemberService.add_member()` |

New resource types are added by registering a new handler — no changes to the Link model or API.

---

## API Routes

```
POST   /api/v1/sharing/links/          → Create a link
GET    /api/v1/sharing/links/          → List own links
GET    /api/v1/sharing/links/<uid>/    → Access link by code (triggers action)
DELETE /api/v1/sharing/links/<uid>/    → Deactivate link
```
