# Ranking — Relationships

```
                    ┌─────────────────────┐
                    │   StudentXP         │  1 row / student
                    │   (denormalized)    │
                    └──────────┬──────────┘
                               │ student_id
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
  ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
  │ XPTransaction    │ │ StudentAch.  │ │ (implicit: the   │
  │ (append log)     │ │ (per code)   │ │  consumer record)│
  └──────────────────┘ └──────────────┘ └──────────────────┘
            │ event_type
            ▼
  ┌──────────────────┐
  │ XPRule           │  bucket=0 / event_type
  │ (config)         │
  └──────────────────┘

  ┌──────────────────┐
  │ LevelConfig      │  bucket=0 / level
  │ (static curve)   │
  └──────────────────┘
```

## Cross-module touchpoints

| Hooked module | Event | XP amount | Counter field |
|---------------|-------|-----------|---------------|
| `classroom_member_service.approve` | `classroom_joined` | 10 | `classrooms_joined_count` |
| `attendance_service.mark_attendance` (status=present) | `attendance_present` | 5 | `attendance_count` |
| `exam_submission_service.submit_exam` (effective) | `exam_submitted` | 20 | — |
| `exam_submission_service.submit_exam` (passed=True) | `exam_passed` | 50 | `exams_passed_count` |
| `quiz_log_service.create` | `quiz_submitted` | 10 | — |
| `quiz_log_service.create` (score ≥ passing) | `quiz_passed` | 15 | `quizzes_passed_count` |
| `quiz_log_service.create` (score == 100) | `quiz_perfect` | 20 | `perfect_scores_count` |
| `doc_note_service.upsert_progress` (is_completed → first time) | `doc_completed` | 10 | — |
| `certificate_issuance_service.check_and_issue` | `certificate_issued` | 200 | `certificates_count` |

## What does NOT trigger XP

- Sending a chat message
- Liking a post / following a user (social actions are out of scope)
- Browsing a classroom (no engagement, no XP)
- Creating a classroom as a teacher (teachers have their own ranking, not
  modeled here)
- Login alone (we update `last_active_date` only when an action fires)
