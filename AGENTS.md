# LMS Backend — Agent Context

This file is the single source of truth for any AI assistant working on this project.
Read this file in full before planning or implementing any task.

---

## What Is This Project?

**LMS Backend** is a REST API + WebSocket server for a Learning Management System built with **Django + Apache Cassandra**. It supports two account types:

- **Space** — Teachers who create and manage classrooms, publish exams, upload materials.
- **Consumer** — Students who join classrooms, view content, and submit assignments.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 4.x + Django REST Framework |
| Database | Apache Cassandra (`django-cassandra-engine`) |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Real-time | Django Channels + Daphne (WebSocket) |
| Storage | Cloudflare R2 (`boto3`) |
| Push Notification | Firebase Admin SDK (FCM + Realtime DB) |
| Dependency Manager | Poetry |

---

## Project Structure

```
LMS_BACKEND/
├── AGENTS.md                    # This file — universal AI context
├── skills/                      # Agent skill workflows (readable by all AIs)
│   └── lms-feature/SKILL.md    # 6-step feature development workflow
├── LMS_SYSTEM/                  # Django settings, urls, asgi
├── core/                        # Shared infrastructure
│   ├── backend/auth/            # JWT auth backend
│   ├── models/                  # BaseTimeStampModel, AbstractAuthModel
│   ├── repositories/            # BaseRepository
│   ├── services/                # BaseService
│   ├── storages/                # Cloudflare R2 StorageService
│   ├── firebase/                # Firebase client, FCM, Realtime DB
│   ├── notification/            # Notification abstraction layer
│   └── ws/                      # WebSocket consumers & routing
└── features/
    ├── account/
    │   ├── consumer/            # Student accounts
    │   └── space/               # Teacher accounts
    ├── course/
    │   └── classroom/           # Classrooms + membership
    ├── resource/                # File upload → R2
    ├── sharing/                 # Shareable invite links
    └── chat/                    # Conversations + messages
```

---

## Architecture Pattern

Every feature follows this strict layered pattern. **Do not skip layers.**

```
ViewSet → Service → Repository → Cassandra Model
```

| Layer | Responsibility |
|-------|----------------|
| **ViewSet** | HTTP in/out, auth check, call service |
| **Service** | Business logic, validation, orchestration |
| **Repository** | All Cassandra queries, wraps ORM |
| **Model** | Cassandra table schema |

### Reference module for pattern: `features/course/classroom/`

---

## Cassandra Conventions

- **Partition key**: `bucket` (Integer, default `0`)
- **Clustering key**: `uid` (UUID v7, `DESC`)
- **Soft delete**: always use `is_deleted = True` + `deleted_at`, never hard delete
- **No foreign keys**: store related UIDs as plain `UUID` columns
- **Indexes**: add secondary index on frequently filtered columns (`teacher_id`, `owner_id`, `email`)
- **Sync schema** after adding/changing a model: `python manage.py sync_cassandra`

---

## API Conventions

```
/api/v1/consumer/...   → Student endpoints
/api/v1/space/...      → Teacher endpoints
/api/v1/resource/...   → File management
/api/v1/sharing/...    → Sharing links
```

- Auth header: `Authorization: Bearer <jwt_access_token>`
- View all endpoints: `python manage.py show_urls`

---

## File Naming Conventions

```
models/          <entity>.py
repositories/    <entity>_repository.py
services/        <entity>_service.py
serializers/     <entity>_serializer.py        (or request/response split)
viewsets/        <entity>_viewset.py
urls.py
```

---

## Module Docs

Detailed specs and design for every module live in `docs/features/<module>/`:

```
docs/features/<module>/
├── specs/
│   ├── overview.md       # Purpose, business context, stakeholders
│   ├── requirements.md   # BR / UR / FR / NFR table
│   ├── workflow.md       # End-to-end flows, actors, edge cases
│   └── rtm.md            # Requirements Traceability Matrix
└── design/
    ├── architecture.md   # Diagrams, components, routing
    ├── entities.md       # Schema, columns, types
    ├── relationships.md  # Entity relationship map
    └── adr.md            # Architecture Decision Records
```

Read the relevant module docs before implementing anything in that module.

---

## Environment Variables

```env
SECRET_KEY=
DEBUG=True

CASSANDRA_HOST=127.0.0.1
CASSANDRA_PORT=9042
CASSANDRA_KEYSPACE=lms_system

R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME_PRIVATE=lms-system
R2_BUCKET_NAME_PUBLIC=lms-system-public
R2_ENDPOINT_URL=
R2_PUBLIC_DOMAIN=

FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=
FIREBASE_CLIENT_ID=
FIREBASE_CLIENT_X509_CERT_URL=
FIREBASE_REGION=asia-southeast1
```

---

## Key Commands

| Command | Description |
|---------|-------------|
| `poetry install` | Install all dependencies |
| `python manage.py runserver` | Start dev server |
| `python manage.py sync_cassandra` | Sync Cassandra schema |
| `python manage.py show_urls` | List all API endpoints |

---

## Development Workflow

When implementing any feature, follow these **6 steps in order**. Do not skip or reorder.

### Step 1 — Plan

Before writing any code:

1. Read `AGENTS.md` (this file) fully.
2. Read the relevant module docs in `docs/features/<module>/`.
3. Identify all files to create or modify.
4. Draft a plan with:
   - Branch name (format: `feature/LMS-<id>-<short-desc>` or `fix/LMS-<id>-<short-desc>`)
   - Files to create / modify
   - Cassandra tables affected (need `sync_cassandra`?)
   - API endpoints to add
   - Any cross-module dependencies
5. Present the plan clearly before writing any code.

### Step 2 — Confirm

1. Show the full plan to the user.
2. Wait for explicit confirmation ("yes", "go", "ok", "confirm").
3. If the user requests changes, update the plan and show it again.
4. **Do not proceed to Step 3 until confirmed.**

### Step 3 — Checkout

After confirmation:

```bash
git checkout -b <branch-name>
```

- Branch format: `feature/LMS-<id>-<short-desc>` for new features
- Branch format: `fix/LMS-<id>-<short-desc>` for bug fixes
- Use kebab-case, lowercase only
- Confirm the branch was created successfully before proceeding.

### Step 4 — Implement

Follow the architecture pattern strictly:

1. **Model** → define Cassandra columns, table name, indexes
2. **Repository** → wrap all Cassandra queries
3. **Service** → business logic, validation, calls repository
4. **Serializer** → request validation + response shape
5. **ViewSet** → thin HTTP handler, calls service
6. **URLs** → register routes
7. **Settings** → add app to `INSTALLED_APPS` if new app
8. Run `python manage.py sync_cassandra` if schema changed.

Rules:
- Never put Cassandra queries in a service or view — always use the repository.
- Never hard delete — always soft delete.
- Follow the naming conventions from this file.
- Do not add comments unless the WHY is non-obvious.

### Step 5 — Push

After implementation:

```bash
# Stage relevant files (never use git add -A blindly)
git add <specific files>

# Commit with clear message
git commit -m "LMS-<id> <short description of what and why>"

# Push branch
git push -u origin <branch-name>

# Create PR
gh pr create \
  --title "LMS-<id> <feature description>" \
  --body "## Summary
- <bullet 1>
- <bullet 2>

## Changes
- <file changes>

## Test
- [ ] sync_cassandra run if schema changed
- [ ] show_urls shows new endpoints
- [ ] Manual test of happy path"
```

### Step 6 — Merge

#### Check prerequisites first:

```bash
# Check gh CLI is authenticated
gh auth status

# Check PR status
gh pr status
```

#### If user confirms merge:

```bash
# Squash and merge
gh pr merge --squash --delete-branch

# Or regular merge
gh pr merge --merge --delete-branch
```

#### If `gh` CLI is not authenticated:

```bash
gh auth login
```

Follow the prompts to authenticate with GitHub.

#### If GitHub MCP is not configured:

Prompt the user:

> GitHub MCP is not configured. To enable AI-powered GitHub operations (auto-merge, PR comments, issue linking), add the GitHub MCP server to your Claude settings:
>
> Run: `! claude mcp add github` or add to `.claude/settings.json`:
> ```json
> {
>   "mcpServers": {
>     "github": {
>       "command": "npx",
>       "args": ["-y", "@modelcontextprotocol/server-github"],
>       "env": {
>         "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
>       }
>     }
>   }
> }
> ```
> After setup, re-run Step 6.

---

## What NOT to Do

- Do not use `git add -A` or `git add .` — stage specific files only.
- Do not skip the Plan and Confirm steps.
- Do not put raw Cassandra queries in ViewSets or Services.
- Do not hard delete any record.
- Do not add fields to models without running `sync_cassandra`.
- Do not create new files without following the naming conventions.
- Do not write code comments that explain WHAT — only explain WHY when non-obvious.
- Do not push directly to `main`.
