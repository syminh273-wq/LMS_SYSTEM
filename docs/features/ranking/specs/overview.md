# Ranking — Overview

## Purpose

Add a **student-facing gamification layer** on top of the LMS. Every
action a student takes (joining a classroom, submitting a quiz, passing
an exam, earning a certificate…) awards **experience points (XP)**.
Accumulated XP drives a **level** curve and unlocks **achievements**.
A **global leaderboard** ranks students by total XP, with optional
weekly/monthly windows.

The pre-existing **per-classroom `LeaderboardService`** (which ranks
students by quiz/exam average inside one classroom) is **kept** and
remains the source of truth for in-classroom competition. The new
*ranking* module is a **complementary**, cross-classroom layer.

## Stakeholders

| Role | What they see | What they can do |
|------|---------------|------------------|
| **Student (consumer)** | Their XP, level, streak, achievements, transaction history, global + per-classroom XP leaderboard | Nothing — read-only views |
| **Teacher (space)** | Per-student XP/level/achievements, per-classroom XP ranking | Nothing — read-only views |
| **System** | Awards XP on every hooked event, evaluates achievements, fires level-up / achievement notifications | Idempotent awarding |

## Out of scope

- Spendable currency / shop
- Friends / guilds / teams
- Streak loss penalties (only `streak_days` tracking; no XP penalty)
- Anti-fraud on rapid XP gain (currently bounded by event idempotency)
- A denormalized global leaderboard table (top-N is read in Python from
  `ranking_student_xps`; OK up to a few thousand students)

## Module map

```
features/ranking/
├── models/        5 Cassandra tables (see design/entities.md)
├── repositories/  thin Cassandra wrappers
├── services/      XPService, AchievementService, LeaderboardService,
│                  LevelService + level_math (pure functions)
├── viewsets/      consumer + space API views
├── consumer_urls.py / space_urls.py
├── defaults.py    seed XP rules
└── apps.py
```
