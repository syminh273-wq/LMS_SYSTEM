"""Global student leaderboard — top-N by total_xp with optional period filter."""
import logging
from datetime import datetime, timedelta
from uuid import UUID

from features.ranking.repositories.student_xp_repository import StudentXPRepository

logger = logging.getLogger(__name__)


class LeaderboardService:
    def __init__(self):
        self.xp_repo = StudentXPRepository()

    def top(self, limit=10, period: str = 'all'):
        """Return top-N by total_xp.

        `period`:
            - 'all'  : all-time (uses total_xp)
            - 'week' : XP gained in last 7 days
            - 'month': XP gained in last 30 days

        For week/month we sum XPTransaction rows in the window.
        """
        limit = max(1, min(int(limit or 10), 100))

        if period == 'all':
            rows = self.xp_repo.get_top(limit=limit)
            return self._hydrate(rows)

        since = datetime.utcnow() - (
            timedelta(days=7) if period == 'week' else timedelta(days=30)
        )
        try:
            from features.ranking.models.xp_transaction import XPTransaction
            qs = XPTransaction.objects.filter(created_at__gte=since).allow_filtering()
            totals = {}
            for tx in qs:
                sid = str(tx.student_id)
                totals[sid] = totals.get(sid, 0) + int(tx.delta_xp or 0)
        except Exception as exc:
            logger.warning(f"[Leaderboard] period query failed: {exc}")
            totals = {}

        sorted_sids = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        top_ids = [UUID(sid) for sid, _ in sorted_sids]
        rows = []
        for sid in top_ids:
            row = self.xp_repo.get(sid)
            if row:
                row.total_xp = totals[str(sid)]
                rows.append(row)
        return self._hydrate(rows)

    def my_rank(self, student_id, period: str = 'all'):
        try:
            sid = UUID(str(student_id))
        except (ValueError, TypeError):
            return None
        me = self.xp_repo.get(sid)
        if not me:
            return None
        my_xp = int(me.total_xp or 0)
        all_rows = list(self.xp_repo.model.objects.all().limit(1000))
        ahead = sum(1 for r in all_rows if int(r.total_xp or 0) > my_xp)
        return {
            'rank': ahead + 1,
            'total_xp': my_xp,
            'level': int(me.level or 1),
            'student_id': str(sid),
        }

    def _hydrate(self, rows):
        from features.account.consumer.repositories import ConsumerRepository
        from features.ranking.services.level_service import level_title
        consumers = ConsumerRepository()
        out = []
        for i, row in enumerate(rows, start=1):
            sid = str(row.student_id)
            name = sid
            avatar = ''
            try:
                c = consumers.find(sid)
                if c is not None:
                    name = getattr(c, 'full_name', '') or getattr(c, 'username', '') or sid
                    avatar = getattr(c, 'avatar_url', '') or ''
            except Exception:
                pass
            level = int(row.level or 1)
            out.append({
                'rank': i,
                'student_id': sid,
                'student_name': name,
                'student_avatar': avatar,
                'total_xp': int(row.total_xp or 0),
                'level': level,
                'level_title': level_title(level),
            })
        return out
