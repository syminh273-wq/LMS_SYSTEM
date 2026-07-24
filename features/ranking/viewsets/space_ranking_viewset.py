"""Teacher-facing ranking endpoints.

    GET /api/v1/space/ranking/students/<uid>/                       — student XP/level
    GET /api/v1/space/ranking/students/<uid>/achievements/          — achievements
    GET /api/v1/space/ranking/students/<uid>/classroom/<cid>/       — student stats in one classroom
    GET /api/v1/space/ranking/classrooms/<uid>/leaderboard/         — unified leaderboard (XP + score)
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views.mixins import UserScopeMixin
from features.ranking.services.xp_service import XPService
from features.ranking.services.achievement_service import AchievementService
from features.ranking.services.unified_leaderboard_service import UnifiedLeaderboardService
from features.ranking.services.level_math import progress_for_xp
from features.ranking.services.level_service import level_title
from features.ranking.serializers.achievement_serializer import AchievementSerializer
from features.ranking.serializers.unified_leaderboard_serializer import (
    UnifiedLeaderboardResponseSerializer,
    StudentClassroomStatsSerializer,
)


def _to_iso(value):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _serialize_student_xp(student_xp, student_id):
    total_xp = int(getattr(student_xp, 'total_xp', 0) or 0)
    level, cur_xp, next_span, pct, to_next, _ = progress_for_xp(total_xp)
    last_active = getattr(student_xp, 'last_active_date', None)
    return {
        'student_id': str(student_id),
        'total_xp': total_xp,
        'level': level,
        'level_title': level_title(level),
        'current_level_xp': cur_xp,
        'next_level_xp': next_span,
        'progress_pct': pct,
        'xp_to_next_level': to_next,
        'streak_days': int(getattr(student_xp, 'streak_days', 0) or 0),
        'last_active_date': _to_iso(last_active),
        'classrooms_joined_count': int(getattr(student_xp, 'classrooms_joined_count', 0) or 0),
        'quizzes_passed_count': int(getattr(student_xp, 'quizzes_passed_count', 0) or 0),
        'exams_passed_count': int(getattr(student_xp, 'exams_passed_count', 0) or 0),
        'perfect_scores_count': int(getattr(student_xp, 'perfect_scores_count', 0) or 0),
        'certificates_count': int(getattr(student_xp, 'certificates_count', 0) or 0),
        'attendance_count': int(getattr(student_xp, 'attendance_count', 0) or 0),
    }


class SpaceRankingStudentViewSet(APIView, UserScopeMixin):
    """GET /api/v1/space/ranking/students/<uid>/"""

    def get(self, request, student_uid):
        xp, _ = XPService().get_or_create(student_uid)
        return Response(_serialize_student_xp(xp, student_uid))


class SpaceRankingAchievementsViewSet(APIView, UserScopeMixin):
    """GET /api/v1/space/ranking/students/<uid>/achievements/"""

    def get(self, request, student_uid):
        data = AchievementService().list_for_student(student_uid)
        return Response(AchievementSerializer(data, many=True).data)


class SpaceRankingStudentClassroomViewSet(APIView, UserScopeMixin):
    """GET /api/v1/space/ranking/students/<uid>/classroom/<cid>/"""

    def get(self, request, student_uid, classroom_uid):
        payload = UnifiedLeaderboardService().build_for_student(
            student_id=student_uid,
            classroom_id=classroom_uid,
        )
        return Response(StudentClassroomStatsSerializer(payload).data)


class SpaceRankingClassroomViewSet(APIView, UserScopeMixin):
    """GET /api/v1/space/ranking/classrooms/<uid>/leaderboard/?limit=20

    Unified leaderboard: each entry contains BOTH the gamification
    (XP / level / level_title) and the academic score
    (quiz_avg / exam_avg / attendance_pct / total_score), plus a
    human-readable `explanation`.
    """

    def get(self, request, classroom_uid):
        try:
            limit = int(request.query_params.get('limit', 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))

        payload = UnifiedLeaderboardService().build_for_classroom(
            classroom_id=classroom_uid,
            current_user_id=None,
            limit=limit,
        )
        return Response(UnifiedLeaderboardResponseSerializer(payload).data)
