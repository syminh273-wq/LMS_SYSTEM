# Classroom Module — Workflows

---

## 1. Create Classroom

### Actors
- **Teacher** (Space account)
- **Platform**

### Preconditions
- Teacher is authenticated.

### Steps
1. Teacher submits POST with `name`, optional `description`, `max_students`.
2. Platform validates input.
3. Platform creates a `Classroom` record with `teacher_id = space.uid`, `status = active`.
4. Platform optionally adds the teacher as a member with `role = teacher`.
5. Classroom record is returned.

### Edge Cases
- **Missing name**: Rejected with a validation error.

---

## 2. Add Student to Classroom

### Actors
- **Teacher**
- **Platform**

### Preconditions
- Teacher is authenticated and owns the classroom.
- Target Consumer exists.

### Steps
1. Teacher submits POST to `/classrooms/<uid>/members/` with `member_id`.
2. Platform verifies the requesting Space is the classroom owner (`teacher_id`).
3. Platform checks no existing active `ClassroomMember` record for this `classroom_uid` + `member_id`.
4. Platform checks `member_count < max_students` (if cap is set).
5. Platform creates `ClassroomMember` with cached `member_name` and `member_avatar`.
6. Membership record is returned.

### Edge Cases
- **Non-owner request**: Returns 403.
- **Already a member**: Returns 400 — duplicate membership rejected.
- **Classroom at capacity**: Returns 400 — max_students exceeded.

---

## 3. Join via Sharing Link

### Actors
- **Student**
- **Platform**

### Preconditions
- Student is authenticated.
- Sharing link exists, is active, and has not expired.

### Steps
1. Student accesses `GET /api/v1/sharing/links/<code>/`.
2. Sharing module validates the link (active, not expired, usage not exceeded).
3. Sharing module identifies `resource_type = classroom` and `action = join`.
4. Platform fetches the classroom by `resource_id`.
5. Platform creates a `ClassroomMember` record for the student.
6. Sharing module increments `used_count`.

### Edge Cases
- **Expired link**: Returns 400 — link expired.
- **Usage limit reached**: Returns 400 — link exhausted.
- **Already a member**: Idempotent — no duplicate record created, success returned.

---

## 4. Remove Student

### Actors
- **Teacher**
- **Platform**

### Preconditions
- Teacher owns the classroom.
- Student is a current member.

### Steps
1. Teacher submits DELETE to `/classrooms/<uid>/members/<member_id>/`.
2. Platform verifies ownership.
3. Platform sets `is_deleted = True` on the `ClassroomMember` record.
4. Student no longer appears in member list.

### Edge Cases
- **Member not found**: Returns 404.
- **Non-owner request**: Returns 403.

---

## 5. Student Lists Classrooms

### Actors
- **Student**
- **Platform**

### Preconditions
- Student is authenticated.

### Steps
1. Student sends GET to `/api/v1/consumer/course/classrooms/`.
2. Platform queries `ClassroomMember` for all records where `member_id = consumer.uid` and `is_deleted = False`.
3. Platform fetches the corresponding `Classroom` records by `classroom_uid`.
4. List is returned sorted by most recently joined.

### Edge Cases
- **No memberships**: Returns an empty list.
