# Skill: lms-feature

## Trigger

`/lms-feature`

## Purpose

Walk through the 6-step LMS feature development workflow. Jira tasks are created and updated **automatically** — you never need to touch the Jira board manually. Just describe what you want to build.

## Prerequisites

Jira MCP must be configured in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://lms-system.atlassian.net",
        "JIRA_USERNAME": "<your-atlassian-email>",
        "JIRA_API_TOKEN": "<your-api-token>"
      }
    }
  }
}
```

Generate API token at: `https://id.atlassian.com/manage-api-tokens`

If MCP is not configured, skip the Jira actions and continue with the workflow — prompt the user to set it up at the end.

---

## Step 1 — Plan

### 1a. Understand the feature

Ask the user:
> "What do you want to build? Describe the feature in one or two sentences."

Do **not** ask for a ticket ID — Claude will create it automatically.

### 1b. Check existing Jira tasks

Use the Jira MCP to list open tasks on the LMS project board:

```
jira_search: project = LMS AND statusCategory != Done ORDER BY created DESC
```

- If a matching task already exists → use it (note the issue key, e.g. `LMS-7`)
- If no matching task exists → go to step 1c

### 1c. Create Jira task automatically

Use Jira MCP to create a new task:

```
jira_create_issue:
  project: LMS
  summary: "<Feature name derived from user's description>"
  description: |
    ## Feature Request
    <Expand on user's description>

    ## Acceptance Criteria
    - [ ] <criterion 1>
    - [ ] <criterion 2>
  issue_type: Task
```

Save the returned issue key (e.g. `LMS-7`) — use it in all subsequent steps.

### 1d. Read project context

1. Read `AGENTS.md` fully.
2. Read `docs/features/<module>/` for all relevant modules (specs + design directories).

### 1e. Draft the implementation plan

Identify and present:

```
## Plan: LMS-<id> — <Feature Name>

### Branch
feature/LMS-<id>-<short-desc>

### Files to Create
- features/<module>/models/<entity>.py
- features/<module>/repositories/<entity>_repository.py
- features/<module>/services/<entity>_service.py
- features/<module>/serializers/<entity>_serializer.py
- features/<module>/viewsets/<entity>_viewset.py
- features/<module>/urls.py

### Files to Modify
- LMS_SYSTEM/settings.py  (INSTALLED_APPS)
- LMS_SYSTEM/urls.py      (include new urls)

### Cassandra
- New table: <table_name> → sync_cassandra required

### API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST   | /api/v1/.../  | Bearer | Create ... |

### Cross-Module Dependencies
- NotificationService (FCM on event X)
- StorageService (R2 upload)
```

### 1f. Post plan as Jira comment

Use Jira MCP to add a comment to the created/found task:

```
jira_add_comment:
  issue_key: LMS-<id>
  comment: |
    ## Implementation Plan

    **Branch**: feature/LMS-<id>-<short-desc>

    **Files to create**: <list>
    **Files to modify**: <list>
    **Cassandra**: <sync required or not>
    **Endpoints**: <list>
```

---

## Step 2 — Confirm

**Do not write any code until this step is complete.**

After presenting the plan, ask the user explicitly:
> "Does this plan look correct? Reply **yes / go / ok / confirm** to proceed, or describe any changes."

- If the user requests changes → update the plan, update the Jira comment, and ask again.
- Only proceed to Step 3 after explicit confirmation ("yes", "go", "ok", "confirm", "đúng", "làm đi").

---

## Step 3 — Checkout + Start Jira Task

### 3a. Create branch

```bash
git checkout -b feature/LMS-<id>-<short-desc>
```

Verify: `git branch --show-current`

### 3b. Transition Jira to In Progress

Use Jira MCP to move the task:

```
jira_transition_issue:
  issue_key: LMS-<id>
  transition: "In Progress"
```

### 3c. Add start comment

```
jira_add_comment:
  issue_key: LMS-<id>
  comment: |
    🚀 Implementation started.

    **Branch**: feature/LMS-<id>-<short-desc>
    **Started at**: <current datetime>
```

---

## Step 4 — Implement

Follow this order strictly — do not skip or reorder:

1. **Model** — Cassandra columns, table name, `Meta.get_keyspace()`, secondary indexes
2. **Repository** — all Cassandra queries wrapped here; no raw queries in service or view
3. **Service** — business logic, validation, calls repository and cross-module services
4. **Serializer** — request validation + response shape (split into request/response files if complex)
5. **ViewSet** — thin HTTP handler: auth check, call service, return response
6. **URLs** — register routes in feature `urls.py` and include in `LMS_SYSTEM/urls.py`
7. **Settings** — add app to `INSTALLED_APPS` if this is a new Django app
8. **sync_cassandra** — run `python manage.py sync_cassandra` if any model was added or changed

Rules (from `AGENTS.md`):
- Never put Cassandra queries in a service or view.
- Never hard delete — always soft delete (`is_deleted = True`, `deleted_at`).
- Follow naming conventions from `AGENTS.md`.
- No comments unless the WHY is non-obvious.

After implementation verify endpoints are registered:

```bash
python manage.py show_urls | grep <new-path>
```

---

## Step 5 — Push

Stage specific files (never `git add -A`):

```bash
git add features/<module>/...
git add LMS_SYSTEM/settings.py   # if modified
git add LMS_SYSTEM/urls.py       # if modified
```

Commit:

```bash
git commit -m "LMS-<id> <short description of what and why>"
```

Push and create PR:

```bash
git push -u origin feature/LMS-<id>-<short-desc>

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
- [ ] Manual test of happy path

Closes LMS-<id>"
```

After PR is created, add comment to Jira:

```
jira_add_comment:
  issue_key: LMS-<id>
  comment: |
    ## Pull Request Created

    **PR**: <pr-url>
    **Branch**: feature/LMS-<id>-<short-desc>

    Ready for review.
```

---

## Step 6 — Merge + Close Jira Task

### 6a. Check prerequisites

```bash
gh auth status
gh pr status
```

### 6b. Merge PR (after user confirms)

```bash
gh pr merge --squash --delete-branch
```

### 6c. Transition Jira to Done

```
jira_transition_issue:
  issue_key: LMS-<id>
  transition: "Done"
```

### 6d. Add close comment

```
jira_add_comment:
  issue_key: LMS-<id>
  comment: |
    ✅ Feature complete and merged.

    **PR**: <pr-url>
    **Merged at**: <current datetime>
    **Branch deleted**: feature/LMS-<id>-<short-desc>
```

### If `gh` is not authenticated

```bash
gh auth login
```

### If Jira MCP is not configured

Prompt the user:

> Jira MCP is not configured. To enable automatic task tracking, add to `~/.claude/settings.json`:
> ```json
> {
>   "mcpServers": {
>     "atlassian": {
>       "command": "uvx",
>       "args": ["mcp-atlassian"],
>       "env": {
>         "JIRA_URL": "https://lms-system.atlassian.net",
>         "JIRA_USERNAME": "<your-email>",
>         "JIRA_API_TOKEN": "<your-api-token>"
>       }
>     }
>   }
> }
> ```
> Generate token at: `https://id.atlassian.com/manage-api-tokens`
> Then restart Claude Code and re-run `/lms-feature`.

---

## Quick Reference

| Step | Action | Jira Auto-Action |
|------|--------|-----------------|
| 1 Plan | Describe feature → read docs → draft plan | Create task (or find existing), post plan as comment |
| 2 Confirm | Wait for explicit yes/go/ok | Update Jira comment if plan changes |
| 3 Checkout | `git checkout -b feature/LMS-<id>-...` | Transition → **In Progress**, comment: started |
| 4 Implement | Model → Repo → Service → Serializer → ViewSet → URLs | — |
| 5 Push | Commit + `gh pr create` | Comment: PR link on Jira task |
| 6 Merge | `gh pr merge --squash` | Transition → **Done**, comment: merged |
