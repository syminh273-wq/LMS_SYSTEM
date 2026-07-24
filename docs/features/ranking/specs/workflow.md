# Ranking — End-to-End Workflow

## 1. Student earns XP

```
[Business service]                          [Ranking module]
                              award()
ExamSubmissionService.submit_exam  ───►  XPService.award(
                                              event_type='exam_submitted',
                                              ref_type='exam_submission',
                                              ref_id=<uid>,
                                          )
                                          │
                                          ├─► XPTransaction row (append)
                                          ├─► StudentXP counters update
                                          ├─► recompute level / progress
                                          ├─► AchievementService.check
                                          │     │
                                          │     └─► may unlock +
                                          │         send notification
                                          └─► if level-up → notification
```

The hook is always last in the business flow and is wrapped in
`try/except` so a ranking failure never breaks the original action.

## 2. Student views profile

```
GET /api/v1/consumer/ranking/me/
  → XPService.get_or_create(student_id)
  → progress_for_xp(total_xp)        (pure math)
  → {level, current_level_xp, next_level_xp, progress_pct, …}
```

## 3. Student views global leaderboard

```
GET /api/v1/consumer/ranking/leaderboard/?period=all&limit=10
  → LeaderboardService.top(limit, period)
  → reads StudentXP (Python sort, top-N)
  → hydrates name/avatar from ConsumerRepository
```

## 4. Teacher views classroom ranking

```
GET /api/v1/space/ranking/classrooms/<uid>/xp/?limit=20
  → ClassroomMemberRepository.get_members(uid)
  → for each member: StudentXPRepository.get(member_id)
  → sort by total_xp DESC
  → hydrate name/avatar
```

## Edge cases handled

- **Soft-deleted exam submission** — `is_effective=False` skips XP.
- **Force-submitted (anti-cheat)** — `force_submitted=True` skips XP.
- **Same event fires twice** — `(event_type, ref_type, ref_id)` dedup
  via `XPTransactionRepository.exists_for_ref`.
- **Student crosses multiple level thresholds in one award** — only
  fires one `level_up` notification (the *final* level); UI can show
  the gap.
- **Streak day rollover** — counted by `last_active_date`; missing
  days reset streak to 1.
- **No rule configured for an event** — awarding becomes a no-op
  (returns `None` silently).
- **Quiz is part of an exam (online mode)** — XP is awarded by the
  underlying `ExamSubmissionService`, not by `QuizLogService.create`,
  to avoid double counting.
