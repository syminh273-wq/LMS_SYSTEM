# Ranking — Architecture

```
                ┌────────────────────────────────────────────┐
                │       Business service (existing)          │
                │  ExamSubmissionService, QuizLogService,    │
                │  AttendanceService, ClassroomMemberService,│
                │  CertificateIssuanceService,               │
                │  DocReadingProgressService                 │
                └────────────────┬───────────────────────────┘
                                 │ XPService.award(...)
                                 ▼
       ┌──────────────────────────────────────────────┐
       │              features/ranking                │
       │  ┌─────────────┐  ┌──────────────────────┐    │
       │  │ XPService   │  │ AchievementService   │    │
       │  └──────┬──────┘  └──────────┬───────────┘    │
       │         │   read/write       │                │
       │  ┌──────▼────────────────────▼───────────┐    │
       │  │       Repositories (5)                │    │
       │  └──────┬────────────────────────────────┘    │
       │         │                                    │
       │  ┌──────▼─────────┐  ┌─────────────────┐      │
       │  │  Models        │  │ level_math.py   │      │
       │  │  (5 Cassandra) │  │ (pure functions)│      │
       │  └────────────────┘  └─────────────────┘      │
       │  ┌─────────────────────────────────────────┐  │
       │  │  LeaderboardService  LevelService       │  │
       │  └─────────────────────────────────────────┘  │
       └────────────────┬─────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  REST endpoints  │
              │  /api/v1/.../ranking/... │
              └──────────────────┘
```

## Why a separate module (not extending `classroom.leaderboard`)?

- `classroom.leaderboard` is a **score** (`quiz_avg × 0.6 + exam_avg × 0.4`)
  computed on the fly, scoped to **one classroom**.
- The new ranking needs **persisted state** (total XP across all
  classrooms), **denormalized counters** (passed quizzes, certificates,
  streak days), and **time-windowed aggregation** (week/month).
- The two are complementary: students see *both* views.

## Hook safety

Every call site uses the pattern:

```python
try:
    from features.ranking.services.xp_service import XPService
    XPService().award(...)
except Exception:
    pass
```

This means:
- A ranking-system failure (Cassandra down, schema drift, model
  not synced) **never breaks** the underlying business flow.
- Errors are silent at the call site but logged at `WARNING` level
  inside `XPService`.

## Level curve

```
required_xp(N) = round(100 * (N-1) ** 1.5)
```

| Level | Required XP | Delta to next |
|------:|------------:|--------------:|
| 1     | 0           | 100           |
| 2     | 100         | 183           |
| 3     | 283         | 237           |
| 5     | 800         | 318           |
| 10    | 2700        | 462           |
| 20    | 8282        | 816           |
| 50    | 34300       | 1537          |
| 100   | 99000       | —             |

The curve is gentle at the start (so new students see early progress)
and steepens later (so the top tiers feel earned).
