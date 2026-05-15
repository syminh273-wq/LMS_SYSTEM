# Classroom Module — Architecture

## Overview

The Classroom module follows the standard LMS layered architecture (ViewSet → Service → Repository → Cassandra). It has two sub-domains: **Classroom** (the room itself) and **ClassroomMember** (membership records), each with independent repository and service layers.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                    Classroom Module                         │
│                                                             │
│  ┌───────────────────────┐   ┌─────────────────────────┐  │
│  │   ClassroomViewSet    │   │ ClassroomMemberViewSet   │  │
│  └──────────┬────────────┘   └───────────┬─────────────┘  │
│             │                            │                  │
│  ┌──────────▼────────────┐   ┌───────────▼─────────────┐  │
│  │   ClassroomService    │   │ ClassroomMemberService   │  │
│  └──────────┬────────────┘   └───────────┬─────────────┘  │
│             │                            │                  │
│  ┌──────────▼────────────┐   ┌───────────▼─────────────┐  │
│  │   ClassroomRepository │   │ ClassroomMemberRepository│  │
│  └──────────┬────────────┘   └───────────┬─────────────┘  │
└─────────────┼──────────────────────────── ┼────────────────┘
              │                             │
   ┌──────────▼──────────┐     ┌────────────▼────────────┐
   │  account_classrooms │     │ course_classroom_members │
   │  (Cassandra)        │     │ (Cassandra)              │
   └─────────────────────┘     └──────────────────────────┘
```

---

## Components

### ClassroomViewSet
Handles CRUD for classrooms. Validates that write operations (update, delete) are performed by the classroom owner. Delegates business logic to `ClassroomService`.

### ClassroomService
- Creates classrooms with `teacher_id = request.user.uid`
- Validates ownership before any mutating operation
- Handles soft delete
- Delegates data access to `ClassroomRepository`

### ClassroomRepository
Wraps Cassandra queries on `account_classrooms`. Key queries:
- `filter(teacher_id=uid)` — list classrooms for a teacher
- `find(uid)` — fetch by primary key (bucket + uid)

### ClassroomMemberViewSet
Handles adding and removing members. Only the classroom owner can add/remove. List endpoint is accessible to both teacher and members.

### ClassroomMemberService
- Validates classroom ownership before adding/removing members
- Checks for duplicate membership
- Enforces `max_students` cap
- Caches `member_name` and `member_avatar` at join time
- Handles soft delete on removal

### ClassroomMemberRepository
Wraps Cassandra queries on `course_classroom_members`. The partition key `classroom_uid` means all members of a classroom are co-located, making member list scans fast.

---

## Sharing Link Integration

`Classroom.resolve_link` is a `@cached_property` that lazily queries the Sharing module's `LinkRepository` for a link where:
- `resource_type = "classroom"`
- `resource_id = classroom.uid`

This avoids an extra API call from the client to get the invite link — it is included in the classroom detail response automatically.

---

## API Routes

```
# Teacher (Space)
GET    /api/v1/space/course/classrooms/
POST   /api/v1/space/course/classrooms/
GET    /api/v1/space/course/classrooms/<uid>/
PUT    /api/v1/space/course/classrooms/<uid>/
DELETE /api/v1/space/course/classrooms/<uid>/
GET    /api/v1/space/course/classrooms/<uid>/members/
POST   /api/v1/space/course/classrooms/<uid>/members/
DELETE /api/v1/space/course/classrooms/<uid>/members/<member_id>/

# Student (Consumer)
GET    /api/v1/consumer/course/classrooms/
GET    /api/v1/consumer/course/classrooms/<uid>/
```
