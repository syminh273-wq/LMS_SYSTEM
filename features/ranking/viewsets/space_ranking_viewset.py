"""Teacher-facing ranking endpoints.

    GET /api/v1/space/ranking/students/<uid>/              — view student XP/achievements
    GET /api/v1/space/ranking/classrooms/<uid>/xp/        — XP leaderboard inside a classroom
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from core.views.mixins import UserScopeMixin
from features.ranking.services.xp_service import XPService
from features.ranking.services.achievement_service import AchievementService
from features.ranking.services.leaderboard_service import LeaderboardService
from features.ranking.repositories.xp_transaction_repository import XPTransactionRepository
from features.ranking.serializers.achievement_serializer import AchievementSerializer


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
    from features.ranking.services.level_math import progress_for_xp
    from features.ranking.services.level_service import level_title
    total_xp = int(getattr(student_xp, 'total_xp', 0) or 0)
    level, cur_xp, next_span, pct, to_next, _ = progress_for_xp(total_xp)
    return {
        'student_id': str(student_id),
        'total_xp': total_xp,
        'level': level,
        'current_level_xp': cur_xp,
        'next_level_xp': next_span,
        'progress_pct': pct,
        'xp_to_next_level': to_next,
        'streak_days': int(getattr(student_xp, 'streak_days', 0) or 0),
        'last_active_date': _to_iso(getattr(student_xp, 'last_active_date', None)),
        'classrooms_joined_count': int(getattr(student_xp, 'classrooms_joined_count', 0) or 0),
        'quizzes_passed_count': int(getattr(student_xp, 'quizzes_passed_count', 0) or 0),
        'exams_passed_count': int(getattr(student_xp, 'exams_passed_count', 0) or 0),
        'perfect_scores_count': int(getattr(student_xp, 'perfect_scores_count', 0) or 0),
        'certificates_count': int(getattr(student_xp, 'certificates_count', 0) or 0),
        'attendance_count': int(getattr(student_xp, 'attendance_count', 0) or 0),
        'level_title': level_title(level),
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


class SpaceRankingClassroomViewSet(APIView, UserScopeMixin):
    """GET /api/v1/space/ranking/classrooms/<uid>/xp/?limit=20

    Returns top-N students in this classroom by total_xp (cross-classroom
    XP, not per-classroom score).
    """

    def get(self, request, classroom_uid):
        from features.course.classroom.repositories.classroom_member_repository import (
            ClassroomMemberRepository,
        )
        try:
            limit = int(request.query_params.get('limit', 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))

        members = list(ClassroomMemberRepository().get_members(classroom_uid))
        member_ids = [str(m.member_id) for m in members]

        rows = []
        for sid in member_ids:
            xp = XPService().get_student_xp(sid)
            if xp is None:
                continue
            rows.append({
                'student_id': sid,
                'total_xp': int(getattr(xp, 'total_xp', 0) or 0),
                'level': int(getattr(xp, 'level', 1) or 1),
            })
        rows.sort(key=lambda r: (-r['total_xp'], r['student_id']))
        for i, row in enumerate(rows, start=1):
            row['rank'] = i

        try:
            from features.account.consumer.repositories import ConsumerRepository
            consumers = ConsumerRepository()
            for row in rows:
                try:
                    c = consumers.find(row['student_id'])
                    if c is not None:
                        row['student_name'] = (
                            getattr(c, 'full_name', '') or
                            getattr(c, 'username', '') or
                            row['student_id']
                        )
                        row['student_avatar'] = getattr(c, 'avatar_url', '') or ''
                    else:
                        row['student_name'] = row['student_id']
                        row['student_avatar'] = ''
                except Exception:
                    row['student_name'] = row['student_id']
                    row['student_avatar'] = ''
        except Exception:
            for row in rows:
                row.setdefault('student_name', row['student_id'])
                row.setdefault('student_avatar', '')

        return Response({
            'classroom_uid': str(classroom_uid),
            'total_students': len(rows),
            'entries': rows[:limit],
        })
