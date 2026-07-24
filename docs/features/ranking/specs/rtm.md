# Ranking — Requirements Traceability Matrix

| Requirement | Implementation |
|-------------|----------------|
| BR-1, FR-1 | `XPService.award` in `features/ranking/services/xp_service.py` |
| BR-2, FR-3 | `level_math.level_for_xp` / `progress_for_xp` in `features/ranking/services/level_math.py` |
| BR-3, FR-4, FR-6 | `AchievementService.check_after_xp_event` in `features/ranking/services/achievement_service.py` |
| BR-4, FR-8, FR-9 | `LeaderboardService.top` in `features/ranking/services/leaderboard_service.py` |
| BR-5 | `SpaceRankingClassroomViewSet` in `features/ranking/viewsets/space_ranking_viewset.py` |
| BR-6, FR-2, NFR-2 | `XPTransactionRepository.exists_for_ref` |
| UR-1, UR-2 | `GET /api/v1/consumer/ranking/me/` → `MeView` |
| UR-3 | `MeView` (includes `streak_days` + `last_active_date`) |
| UR-4 | `GET /api/v1/consumer/ranking/me/transactions/` |
| UR-5, UR-6 | `GET /api/v1/consumer/ranking/me/achievements/` |
| UR-7 | `GET /api/v1/consumer/ranking/leaderboard/` |
| UR-8 | `GET /api/v1/consumer/ranking/me/leaderboard/` |
| UR-9 | `GET /api/v1/space/ranking/students/<uid>/` |
| UR-10 | `GET /api/v1/space/ranking/classrooms/<uid>/xp/` |
| NFR-1 | All hooks use `try/except` and `logger.warning` |
| NFR-3 | `_to_iso` helper in viewsets |
| NFR-5 | `bucket=0` for global config tables, `student_id` partition for per-student |
