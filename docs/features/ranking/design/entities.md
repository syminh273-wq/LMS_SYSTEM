# Ranking — Entities

## `ranking_student_xps`

| Column | Type | Notes |
|--------|------|-------|
| `student_id` | UUID | **PK** |
| `total_xp` | BigInt | Sum of all `delta_xp` for this student |
| `level` | Int | Cached `level_for_xp(total_xp)` |
| `current_level_xp` | BigInt | XP earned since reaching `level` |
| `next_level_xp` | BigInt | Total span of current level |
| `streak_days` | Int | Consecutive active days |
| `last_active_date` | Date | For streak math |
| `last_active_at` | DateTime | Audit |
| `classrooms_joined_count` | Int | Counter |
| `quizzes_passed_count` | Int | Counter |
| `exams_passed_count` | Int | Counter |
| `perfect_scores_count` | Int | Counter |
| `certificates_count` | Int | Counter |
| `attendance_count` | Int | Counter |
| `updated_at` | DateTime | Audit |

One row per student. Read on every profile render — O(1).

## `ranking_xp_transactions`

| Column | Type | Notes |
|--------|------|-------|
| `student_id` | UUID | **Partition key** |
| `uid` | UUID | **Clustering key**, UUIDv7 DESC = newest first |
| `created_at` | DateTime | (secondary sort) |
| `event_type` | Text | indexed; matches a row in `ranking_xp_rules` |
| `delta_xp` | Int | always > 0 (losses not modeled) |
| `ref_type` | Text | e.g. `exam_submission`, `quiz_log` |
| `ref_id` | UUID | The source entity's uid |
| `classroom_id` | UUID | indexed; nullable |
| `description` | Text | human-readable |
| `metadata` | Text (JSON) | free-form context |

Used for:
- `/me/transactions/` history
- Idempotency: `(student_id, event_type, ref_type, ref_id)` must be
  unique per student.

## `ranking_achievements`

| Column | Type | Notes |
|--------|------|-------|
| `student_id` | UUID | **Partition key** |
| `achievement_code` | Text | **Clustering key** (e.g. `first_quiz`) |
| `title`, `description`, `icon` | Text | copied from catalog |
| `is_unlocked` | Boolean | |
| `unlocked_at` | DateTime | set when first unlocked |
| `target_value` | Int | e.g. 10 for `attend_10` |
| `current_value` | Int | counter snapshot |
| `progress_pct` | Int | 0–100 |
| `updated_at` | DateTime | |

## `ranking_level_configs`

| Column | Type | Notes |
|--------|------|-------|
| `bucket` | Int | **PK**, always 0 |
| `level` | Int | **Clustering key** |
| `required_xp` | BigInt | matches `level_math.required_xp_for_level` |
| `title` | Text | e.g. `Tân binh`, `Cao thủ` |
| `color` | Text | UI hint |

## `ranking_xp_rules`

| Column | Type | Notes |
|--------|------|-------|
| `bucket` | Int | **PK**, always 0 |
| `event_type` | Text | **Clustering key** |
| `xp_amount` | Int | points awarded |
| `is_active` | Boolean | turn off without deleting |
| `description` | Text | for admin UIs |

## Indexes

- `ranking_xp_transactions.event_type` — global event filtering
- `ranking_xp_transactions.classroom_id` — per-classroom history
- All other queries are partition-scoped and don't need secondary
  indexes.
