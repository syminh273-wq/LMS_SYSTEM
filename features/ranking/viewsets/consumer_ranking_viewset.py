"""Student-facing ranking endpoints.

    GET /api/v1/consumer/ranking/me/                       — current XP/level/streak
    GET /api/v1/consumer/ranking/me/transactions/         — XP history
    GET /api/v1/consumer/ranking/me/achievements/         — achievement list
    GET /api/v1/consumer/ranking/me/leaderboard/          — my global rank
    GET /api/v1/consumer/ranking/leaderboard/?period=...  — top-N
    GET /api/v1/consumer/ranking/levels/                  — level catalog
    GET /api/v1/consumer/ranking/achievements/catalog/    — achievement catalog
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views.mixins import UserScopeMixin
from features.ranking.services.xp_service import XPService
from features.ranking.services.achievement_service import AchievementService
from features.ranking.services.leaderboard_service import LeaderboardService
from features.ranking.services.level_service import all_levels, level_title
from features.ranking.services.level_math import progress_for_xp
from features.ranking.serializers.student_xp_serializer import StudentXPSerializer
from features.ranking.serializers.xp_transaction_serializer import XPTransactionSerializer
from features.ranking.serializers.achievement_serializer import AchievementSerializer
from features.ranking.serializers.leaderboard_serializer import (
    LeaderboardResponseSerializer, MyRankSerializer,
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
        'level_title': level_title(level),
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
    def get(self, request):
        sid = self._me_id(request)
        try:
            limit = int(request.query_params.get('limit', 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 200))
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
