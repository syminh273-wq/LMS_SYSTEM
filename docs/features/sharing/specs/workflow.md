# Sharing Module — Workflows

---

## 1. Create Sharing Link

### Actors
- **Teacher** (Space account)
- **Platform**

### Preconditions
- Teacher is authenticated and owns the resource being linked.

### Steps
1. Teacher submits POST with `resource_type`, `resource_id`, `action`, optional `expired_at`, `max_usage`.
2. Platform validates input.
3. Platform generates a unique `code` (short alphanumeric string).
4. Platform creates a `Link` record with `is_active = True`, `used_count = 0`.
5. Link record including the code is returned.
6. Teacher shares the link URL with students.

### Edge Cases
- **Code collision**: If the generated code already exists, regenerate until unique (extremely rare).

---

## 2. Access a Sharing Link (Student Joins Classroom)

### Actors
- **Student** (Consumer account)
- **Platform**

### Preconditions
- Student is authenticated.
- Link exists with `resource_type = classroom`.

### Steps
1. Student sends GET to `/api/v1/sharing/links/<code>/`.
2. Platform looks up the Link by `code`.
3. Platform checks `is_active = True`.
4. Platform checks `expired_at` — if set and in the past, returns 400.
5. Platform checks `used_count < max_usage` — if `max_usage > 0` and exhausted, returns 400.
6. Platform identifies `resource_type = classroom` and `action = join`.
7. Platform fetches the classroom by `resource_id`.
8. Platform creates a `ClassroomMember` record for the student (if not already a member).
9. Platform increments `used_count` on the Link.
10. Success response returned.

### Edge Cases
- **Already a member**: Step 8 is idempotent — no duplicate record created, still returns success.
- **Link not found**: Returns 404.
- **Link expired**: Returns 400 with expiry message.
- **Link exhausted**: Returns 400 with usage limit message.
- **Classroom not found**: Returns 404 — resource_id points to deleted classroom.

---

## 3. Deactivate Link

### Actors
- **Teacher**
- **Platform**

### Steps
1. Teacher sends DELETE to `/api/v1/sharing/links/<uid>/`.
2. Platform verifies the requesting user created the link (ownership check).
3. Platform sets `is_active = False`.
4. Future accesses to this link return 400 (inactive link).
