# Resource Module — Architecture

## Overview

The Resource module follows the standard LMS layered architecture. Its distinguishing feature is the `StorageService` — an external integration layer that abstracts file storage (Cloudflare R2 or local) from the rest of the module.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────┐
│               Resource Module                 │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │           ResourceViewSet               │ │
│  └──────────────────┬────────────────────── ┘ │
│                     │                          │
│  ┌──────────────────▼────────────────────── ┐ │
│  │           ResourceService               │ │
│  └────────┬─────────────────────┬───────── ┘ │
│           │                     │             │
│  ┌────────▼─────────┐  ┌────────▼──────────┐ │
│  │ ResourceRepository│  │  StorageService   │ │
│  └────────┬─────────┘  └────────┬──────────┘ │
└───────────┼─────────────────────┼─────────────┘
            │                     │
   ┌────────▼──────────┐  ┌───────▼──────────┐
   │ resource_resources│  │  Cloudflare R2   │
   │ (Cassandra)       │  │  (or local disk) │
   └───────────────────┘  └──────────────────┘
```

---

## Components

### ResourceViewSet
Handles upload, list, detail, and soft delete. The upload action calls `StorageService` before creating the Cassandra record.

### ResourceService
Orchestrates the upload flow: validates input, calls `StorageService`, creates the `Resource` record, and returns the response.

### ResourceRepository
Wraps Cassandra queries on `resource_resources`. Key queries:
- `filter(owner_id=uid)` — owner-scoped list
- `find(uid)` — fetch by primary key

### StorageService (`core/storages/storage_service.py`)
S3-compatible Cloudflare R2 client built on `boto3`. Key behaviors:
- Initializes lazily on first use
- Falls back to `save_local()` if R2 is not configured
- Generates public CDN URLs from `R2_PUBLIC_DOMAIN`
- Supports separate public and private buckets

---

## File Key Strategy

Uploaded files are stored with the key pattern:
```
uploads/<owner_type>/<owner_uid>/<resource_uid>/<original_filename>
```

This provides natural namespacing by owner and avoids filename collisions.
