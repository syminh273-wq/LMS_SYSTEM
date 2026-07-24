"""Centralized XP awarding. Hooked from exam/quiz/attendance/cert/doc/classroom
services. Idempotent per (student, event_type, ref_type, ref_id)."""
import json
import logging
from datetime import datetime, date
from uuid import UUID

from features.ranking.repositories.student_xp_repository import StudentXPRepository
from features.ranking.repositories.xp_transaction_repository import XPTransactionRepository
from features.ranking.repositories.xp_rule_repository import XPRuleRepository
from features.ranking.services.level_math import (
    required_xp_for_level,
    level_for_xp,
)

logger = logging.getLogger(__name__)


class XPService:
    def __init__(self):
        self.xp_repo = StudentXPRepository()
        self.tx_repo = XPTransactionRepository()
        self.rule_repo = XPRuleRepository()
        try:
            from features.ranking.defaults import seed_default_rules
            seed_default_rules(self.rule_repo)
        except Exception:
            pass

    def _safe_uuid(self, val):
        if val is None:
            return None
        if isinstance(val, UUID):
            return val
        try:
            return UUID(str(val))
        except (ValueError, TypeError):
            return None

    def award(
        self,
        student_id,
        event_type: str,
        *,
        delta_xp: int = None,
        ref_type: str = None,
        ref_id=None,
        classroom_id=None,
        description: str = '',
        metadata: dict = None,
        count_field: str = None,
        increment: int = 1,
    ):
        """Award XP for an event.

        Idempotency: if a transaction already exists for the same
        (student_id, event_type, ref_type, ref_id), this is a no-op.

        Returns the XPTransaction (or None if no-op / student invalid).
        """
        sid = self._safe_uuid(student_id)
        if sid is None:
            return None

        rid = self._safe_uuid(ref_id) if ref_id is not None else None
        cid = self._safe_uuid(classroom_id) if classroom_id is not None else None

        if delta_xp is None:
            delta_xp = self.rule_repo.get_amount(event_type, default=0)
        if not delta_xp:
            return None

        try:
            delta_xp = int(delta_xp)
        except (TypeError, ValueError):
            return None

        if ref_type and rid is not None:
            if self.tx_repo.exists_for_ref(sid, event_type, ref_type, rid):
                return None

        student_xp, _ = self.xp_repo.get_or_create(sid)

        now = datetime.utcnow()
        new_total = max(0, int(student_xp.total_xp or 0) + delta_xp)
        new_level = level_for_xp(new_total)
        prev_level = int(student_xp.level or 1)

        cur_required = required_xp_for_level(new_level)
        next_required = required_xp_for_level(new_level + 1)
        current_level_xp = max(0, new_total - cur_required)
        next_level_xp = max(0, next_required - cur_required) if new_level < 100 else 0

        streak_days = int(student_xp.streak_days or 0)
        last_active = getattr(student_xp, 'last_active_date', None)
        today = date.today()
        if last_active is None:
            streak_days = 1
        else:
            if last_active == today:
                pass
            elif (today - last_active).days == 1:
                streak_days += 1
            else:
                streak_days = 1

        updates = {
            'total_xp': new_total,
            'level': new_level,
            'current_level_xp': current_level_xp,
            'next_level_xp': next_level_xp,
            'streak_days': streak_days,
            'last_active_date': today,
            'last_active_at': now,
        }

        if count_field:
            current_val = int(getattr(student_xp, count_field, 0) or 0)
            updates[count_field] = current_val + int(increment or 0)

        try:
            tx = self.tx_repo.create(
                student_id=sid,
                event_type=event_type,
                delta_xp=delta_xp,
                ref_type=ref_type or '',
                ref_id=rid,
                classroom_id=cid,
                description=description or event_type,
                metadata=metadata or {},
            )
        except Exception as exc:
            logger.warning(f"[XP] failed to write transaction: {exc}")
            return None

        try:
            self.xp_repo.update_counters(student_xp, **updates)
        except Exception as exc:
            logger.warning(f"[XP] failed to update counters: {exc}")

        if new_level > prev_level:
            try:
                self._notify_level_up(sid, prev_level, new_level, new_total)
            except Exception as exc:
                logger.warning(f"[XP] level-up notification failed: {exc}")

        try:
            from features.ranking.services.achievement_service import AchievementService
            fresh = self.xp_repo.get(sid)
            if fresh is not None:
                AchievementService().check_after_xp_event(
                    student_id=sid,
                    event_type=event_type,
                    student_xp=fresh,
                )
        except Exception as exc:
            logger.warning(f"[XP] achievement check failed: {exc}")

        return tx

    def get_or_create(self, student_id):
        return self.xp_repo.get_or_create(self._safe_uuid(student_id))

    def get_student_xp(self, student_id):
        return self.xp_repo.get(self._safe_uuid(student_id))

    def get_transactions(self, student_id, limit=20, event_type=None, classroom_id=None):
        return self.tx_repo.list_by_student(
            student_id, limit=limit,
            event_type=event_type, classroom_id=classroom_id,
        )

    def _notify_level_up(self, student_id, old_level, new_level, total_xp):
        from features.notification.services.notification_service import NotificationService
        NotificationService().send_notification(
            target_uid=str(student_id),
            notify_type='ranking_level_up',
            title=f'🎉 Bạn đã lên cấp {new_level}!',
            content=f'Chúc mừng! Bạn vừa đạt cấp {new_level} với {total_xp} XP.',
            metadata={
                'old_level': old_level,
                'new_level': new_level,
                'total_xp': total_xp,
            },
        )
