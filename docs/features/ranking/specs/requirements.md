# Ranking — Requirements

## Business Requirements (BR)

| ID | Description |
|----|-------------|
| BR-1 | Every learning action a student completes shall award XP. |
| BR-2 | XP must accumulate into a visible level so students see progression. |
| BR-3 | Achievements shall unlock automatically when students hit milestones. |
| BR-4 | A global leaderboard shall rank students by total XP. |
| BR-5 | A per-classroom XP ranking shall exist for teachers. |
| BR-6 | XP for the same event must never be awarded twice (idempotency). |

## User Requirements (UR)

| ID | As a | I want to | So that |
|----|------|-----------|----------|
| UR-1 | student | see my total XP and level | I know how far I've progressed |
| UR-2 | student | see XP to next level | I know what to aim for next |
| UR-3 | student | see my daily streak | I stay consistent |
| UR-4 | student | see XP history | I understand what gave me XP |
| UR-5 | student | see which achievements I have unlocked | I feel rewarded |
| UR-6 | student | see in-progress achievements with progress | I have a goal to chase |
| UR-7 | student | see top-N students globally | I have someone to compete with |
| UR-8 | student | see my global rank | I know where I stand |
| UR-9 | teacher | view a student's XP/level/achievements | I can motivate them |
| UR-10 | teacher | see XP ranking inside my classroom | I can recognize top students |

## Functional Requirements (FR)

| ID | Description |
|----|-------------|
| FR-1 | `XPService.award(student_id, event_type, ref_type, ref_id, …)` writes a transaction + updates the per-student counter atomically. |
| FR-2 | Awarding the same `(student_id, event_type, ref_type, ref_id)` twice is a no-op. |
| FR-3 | `level_for_xp(total_xp)` is deterministic and matches the published curve `100 × (N-1)^1.5`. |
| FR-4 | `AchievementService.check_after_xp_event` runs after every `award` and may unlock one or more achievements. |
| FR-5 | When a level-up occurs, a `ranking_level_up` notification is sent. |
| FR-6 | When an achievement is unlocked, a `ranking_achievement_unlocked` notification is sent. |
| FR-7 | Default XP rules are seeded into `ranking_xp_rules` on first read. |
| FR-8 | Global leaderboard top-N is sorted by `(total_xp DESC, student_id ASC)`. |
| FR-9 | Weekly/monthly leaderboards sum `XPTransaction.delta_xp` in the time window. |
| FR-10 | All endpoints require JWT auth. |

## Non-Functional Requirements (NFR)

| ID | Description |
|----|-------------|
| NFR-1 | All writes to `ranking_*` must not block the calling business flow — every hook is wrapped in `try/except`. |
| NFR-2 | Idempotency is enforced at the data layer, not by the caller. |
| NFR-3 | API responses must serialize DateTime/Date as ISO 8601 strings. |
| NFR-4 | Top-N leaderboard query must complete in <500ms for up to 1k students (Python sort). |
| NFR-5 | The new tables follow the same Cassandra conventions as the rest of the system (`bucket=0` for global configs, `student_id` as partition for per-student data). |

## Default XP rules (v1)

| Event | XP |
|-------|----|
| `classroom_joined` | 10 |
| `attendance_present` | 5 |
| `exam_submitted` | 20 |
| `exam_passed` | 50 |
| `quiz_submitted` | 10 |
| `quiz_passed` | 15 |
| `quiz_perfect` | 20 |
| `doc_completed` | 10 |
| `collection_completed` | 100 |
| `certificate_issued` | 200 |

These are stored in `ranking_xp_rules` and can be edited without a
code change.
