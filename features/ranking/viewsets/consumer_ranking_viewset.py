"""Student-facing ranking endpoints.

    GET /api/v1/consumer/ranking/me/                            — current XP/level/streak
    GET /api/v1/consumer/ranking/me/transactions/              — full XP history (FE paginates)
    GET /api/v1/consumer/ranking/me/achievements/              — achievement list
    GET /api/v1/consumer/ranking/me/leaderboard/               — my global rank
    GET /api/v1/consumer/ranking/leaderboard/?period=...       — top-N
    GET /api/v1/consumer/ranking/levels/                       — level catalog
    GET /api/v1/consumer/ranking/achievements/catalog/         — achievement catalog
    GET /api/v1/consumer/ranking/classrooms/<uid>/leaderboard/ — unified per-classroom leaderboard
    GET /api/v1/consumer/ranking/me/classroom/<uid>/           — my stats in one classroom
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views.mixins import UserScopeMixin
from features.ranking.services.xp_service import XPService
from features.ranking.services.achievement_service import AchievementService
from features.ranking.services.leaderboard_service import LeaderboardService
from features.ranking.services.unified_leaderboard_service import UnifiedLeaderboardService
from features.ranking.services.level_service import all_levels, level_title
from features.ranking.services.level_math import progress_for_xp
from features.ranking.services.explanation_resolver import explain_xp_history_row
from features.ranking.serializers.student_xp_serializer import StudentXPSerializer
from features.ranking.serializers.xp_transaction_serializer import XPTransactionSerializer
from features.ranking.serializers.achievement_serializer import AchievementSerializer
from features.ranking.serializers.leaderboard_serializer import (
    LeaderboardResponseSerializer, MyRankSerializer,
)
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


class _BaseConsumerRankingView(APIView, UserScopeMixin):
    def _me_id(self, request):
        return str(request.user.uid)


class MeView(_BaseConsumerRankingView):
    def get(self, request):
        sid = self._me_id(request)
        student_xp, _ = XPService().get_or_create(sid)
        payload = _serialize_student_xp(student_xp, sid)
        return Response(StudentXPSerializer(payload).data)


class MeTransactionsView(_BaseConsumerRankingView):
    """Full XP history for the current student.

    Returns the full list (no backend pagination) so the FE can paginate
    however it wants. Optional query params:
        - event_type  : filter by event_type (e.g. quiz_passed)
        - classroom_id : filter to one classroom
        - limit       : safety cap (default 500, max 2000)
    """

    def get(self, request):
        sid = self._me_id(request)
        try:
            limit = int(request.query_params.get('limit') or 500)
        except (TypeError, ValueError):
            limit = 500
        limit = max(1, min(limit, 2000))
        event_type = request.query_params.get('event_type') or None
        classroom_id = request.query_params.get('classroom_id') or None
        txs = XPService().get_transactions(
            sid, limit=limit,
            event_type=event_type, classroom_id=classroom_id,
        )
        out = []
        for t in txs:
            out.append({
                'uid': str(t.uid),
                'event_type': t.event_type,
                'delta_xp': int(t.delta_xp or 0),
                'ref_type': t.ref_type or '',
                'ref_id': str(t.ref_id) if t.ref_id else None,
                'classroom_id': str(t.classroom_id) if t.classroom_id else None,
                'description': t.description or '',
                'explanation': explain_xp_history_row(t),
                'created_at': _to_iso(t.created_at),
            })
        return Response(XPTransactionSerializer(out, many=True).data)


class MeAchievementsView(_BaseConsumerRankingView):
    def get(self, request):
        sid = self._me_id(request)
        data = AchievementService().list_for_student(sid)
        return Response(AchievementSerializer(data, many=True).data)


class MeLeaderboardView(_BaseConsumerRankingView):
    def get(self, request):
        sid = self._me_id(request)
        period = request.query_params.get('period', 'all')
        rank = LeaderboardService().my_rank(sid, period=period)
        if rank is None:
            return Response({'rank': None, 'total_xp': 0, 'level': 1, 'student_id': sid})
        return Response(MyRankSerializer(rank).data)


class LeaderboardView(_BaseConsumerRankingView):
    def get(self, request):
        period = request.query_params.get('period', 'all')
        try:
            limit = int(request.query_params.get('limit', 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))
        entries = LeaderboardService().top(limit=limit, period=period)
        return Response(LeaderboardResponseSerializer({
            'period': period,
            'total_students': len(entries),
            'entries': entries,
        }).data)


class LevelsView(_BaseConsumerRankingView):
    def get(self, request):
        return Response({'levels': all_levels()})


class AchievementsCatalogView(_BaseConsumerRankingView):
    def get(self, request):
        return Response({'achievements': AchievementService().catalog()})


class ClassroomLeaderboardView(_BaseConsumerRankingView):
    """GET /api/v1/consumer/ranking/classrooms/<uid>/leaderboard/?limit=20

    Unified leaderboard for the current student: each entry has both
    gamification (XP / level) and academic score, plus an `explanation`.
    Only members of the classroom can view.
    """

    def get(self, request, classroom_uid):
        from features.course.classroom.services.classroom_member_service import ClassroomMemberService
        from rest_framework import status

        if not ClassroomMemberService().is_member(str(classroom_uid), request.user.uid):
            return Response(
                {'error': 'Bạn cần tham gia lớp để xem bảng xếp hạng.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            limit = int(request.query_params.get('limit', 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))

        payload = UnifiedLeaderboardService().build_for_classroom(
            classroom_id=classroom_uid,
            current_user_id=str(request.user.uid),
            limit=limit,
        )
        return Response(UnifiedLeaderboardResponseSerializer(payload).data)


class MeClassroomStatsView(_BaseConsumerRankingView):
    """GET /api/v1/consumer/ranking/me/classroom/<uid>/"""

    def get(self, request, classroom_uid):
        payload = UnifiedLeaderboardService().build_for_student(
            student_id=str(request.user.uid),
            classroom_id=classroom_uid,
        )
        return Response(StudentClassroomStatsSerializer(payload).data)
