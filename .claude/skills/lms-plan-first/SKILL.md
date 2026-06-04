---
name: lms-plan-first
description: Use for any LMS Backend feature, bug fix, refactor, schema change, API change, or code implementation request. Forces Claude to read project context, prepare an implementation plan, and wait for explicit user confirmation before writing code.
---

# LMS Plan First

## Non-Negotiable Rule

For any request that may change code, configuration, database schema, routes, docs, tests, or project files:

1. Read `AGENTS.md` fully before planning.
2. Read relevant module docs under `docs/features/<module>/` when the request maps to an existing or new feature module.
3. Inspect the existing code pattern before proposing changes.
4. Present a concrete plan.
5. Stop and wait for explicit confirmation before coding.

Do not create, edit, delete, stage, commit, push, or merge files before confirmation.

Explicit confirmation means the user replies with one of:

- `yes`
- `go`
- `ok`
- `confirm`
- `approved`
- `đúng`
- `làm đi`

If the user asks for changes to the plan, update the plan and ask for confirmation again.

## Required Plan Format

Present the plan with these sections:

```markdown
## Plan: <Ticket or short task name>

### Branch
feature/LMS-<id>-<short-desc>
```

Use `fix/LMS-<id>-<short-desc>` for bug fixes. If there is no ticket ID, use `feature/lms-unknown-<short-desc>` or ask whether a Jira ticket should be created.

```markdown
### Context Read
- AGENTS.md
- docs/features/<module>/...
- Existing reference code: <paths>

### Files to Create
- <path>

### Files to Modify
- <path>

### Cassandra
- Tables affected: <none/table names>
- Schema sync required: <yes/no>

### API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| ...    | ...  | ...  | ...         |

### Cross-Module Dependencies
- <dependency or none>

### Verification
- <commands/manual checks>
```

End with:

```markdown
Does this plan look correct? Reply `yes`, `go`, `ok`, or `confirm` to proceed, or describe changes.
```

## Implementation Rules After Confirmation

After confirmation, follow the project workflow in `AGENTS.md`:

1. Create the branch with `git checkout -b <branch-name>`.
2. Implement in layer order:
   - Model
   - Repository
   - Service
   - Serializer
   - ViewSet
   - URLs
   - Settings, only if needed
3. Keep Cassandra queries inside repositories only.
4. Use soft delete only; never hard delete records.
5. Run `python manage.py sync_cassandra` if any Cassandra model changed.
6. Verify affected endpoints and behavior.
7. Stage only specific files; never use `git add -A` or `git add .`.

## Exceptions

For read-only requests such as explanation, review, search, diagnostics, or command output, do not require confirmation unless the next step would modify files or external state.
