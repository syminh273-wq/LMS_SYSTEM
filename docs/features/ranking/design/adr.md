# Ranking — Architecture Decision Records

## ADR-1: New module, not extension of `classroom.leaderboard`

**Status:** Accepted.

**Context:** The existing `LeaderboardService.build()` (in
`features/course/classroom/services/leaderboard_service.py`) ranks
students inside a single classroom using per-classroom quiz/exam
averages. The new requirement is global XP / level / achievements,
which needs persisted state across all classrooms.

**Decision:** Build a new `features/ranking/` module. Keep
`classroom.leaderboard` untouched — it is still the right answer for
"who's top in *this* class?".

**Consequences:**
- Two separate leaderboards coexist (per-classroom, global).
- The same student can show up in both with different ranks — this is
  intentional and surfaced as two separate UI cards.
- No migration of existing leaderboard data is needed.

## ADR-2: Idempotency via `(event_type, ref_type, ref_id)`

**Status:** Accepted.

**Context:** Several business flows can call the same XP award twice
(e.g. retrying a submit, force-submit + manual submit). A simple
boolean flag is not enough because the same student may legitimately
retry a quiz — each attempt is its own event.

**Decision:** XP is idempotent per `(student_id, event_type, ref_type,
ref_id)`. The XP service queries `XPTransaction.exists_for_ref` before
inserting. If the same ref is seen twice, it's a no-op.

**Consequences:**
- A `quiz_log` with `uid=X` can only award `quiz_submitted` once.
- A `classroom_member` (one per `(classroom_uid, member_id)`) can only
  award `classroom_joined` once per classroom.
- If a new flow needs different idempotency, it must use a different
  `ref_type` (e.g. `quiz_attempt` vs `quiz_log`).

## ADR-3: Per-student denormalized `StudentXP` + append-only ledger

**Status:** Accepted.

**Context:** A naive design would compute level/XP by reading all
`XPTransaction` rows. This is O(N) on every profile render.

**Decision:** Maintain a single denormalized `StudentXP` row per
student (write-through on every `award`) for O(1) reads. The
`XPTransaction` log is kept for history and idempotency.

**Consequences:**
- Profile screen is fast (one row read).
- Replays are safe (idempotency check + log is authoritative).
- Inconsistency window: if the process crashes between writing the
  transaction and updating the counter, the counter may lag by 1
  award. Acceptable: the next award will recompute correctly, or
  backfill is trivial.

## ADR-4: Notification via existing `NotificationService`

**Status:** Accepted.

**Context:** We need to notify students on level-up and achievement
unlock. The codebase already has a `NotificationService` that writes to
`NotificationLog` + pushes to Firebase Realtime DB.

**Decision:** Reuse `NotificationService` with two new `notify_type`
values: `ranking_level_up` and `ranking_achievement_unlocked`. No new
notification infrastructure.

**Consequences:**
- Students see rank events in the same bell icon as everything else.
- Realtime fan-out works out of the box (Firebase).
- Easy to filter / mute in the future via the existing
  `StudentProfileSettings`.

## ADR-5: Top-N leaderboard is read in Python

**Status:** Accepted (with caveat).

**Context:** Cassandra cannot order by a non-clustering column. To
return "top 10 by total_xp" we would need either:
- A denormalized top-N table updated on every award (write amplification)
- A scan + sort in Python (read amplification on demand)

**Decision:** Read in Python, capped at 1k rows.

**Consequences:**
- O(1k) scan per leaderboard request.
- Acceptable for the expected user base (a few thousand active
  students).
- For > 10k students, replace with a denormalized top table.

## ADR-6: Hook into existing services via late try/except

**Status:** Accepted.

**Context:** XP awarding is a *side effect* of business actions. A
ranking failure must not roll back a successful exam submission.

**Decision:** Every hook is wrapped in `try/except Exception: pass`
and lives at the *end* of the business flow (after the DB write
succeeds). Failures are logged but not surfaced to the user.

**Consequences:**
- Worst case: a student misses an XP award. We accept this — the
  alternative (rolling back a submission) is worse for trust.
- A periodic reconciliation job (out of scope) could replay missed
  events from the source tables.
