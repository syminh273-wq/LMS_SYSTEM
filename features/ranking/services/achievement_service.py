"""Achievement definitions + auto-unlock.

The catalog is static (12 achievements). On every XP event, the service
re-evaluates relevant achievements for that student.
"""
import logging
from datetime import datetime

from features.ranking.repositories.achievement_repository import AchievementRepository

logger = logging.getLogger(__name__)


ACHIEVEMENT_CATALOG = [
    {
        'code': 'first_quiz',
        'title': 'Khởi đầu',
        'description': 'Hoàn thành bài quiz đầu tiên',
        'icon': 'play_circle',
        'target_value': 1,
        'count_field': 'quizzes_passed_count',
    },
    {
        'code': 'first_exam',
        'title': 'Vượt ải',
        'description': 'Đậu bài exam đầu tiên',
        'icon': 'school',
        'target_value': 1,
        'count_field': 'exams_passed_count',
    },
    {
        'code': 'first_cert',
        'title': 'Tốt nghiệp',
        'description': 'Nhận chứng chỉ đầu tiên',
        'icon': 'verified',
        'target_value': 1,
        'count_field': 'certificates_count',
    },
    {
        'code': 'perfect_score',
        'title': 'Hoàn hảo',
        'description': 'Đạt 100% trong một quiz',
        'icon': 'star',
        'target_value': 1,
        'count_field': 'perfect_scores_count',
    },
    {
        'code': 'attend_10',
        'title': 'Chuyên cần',
        'description': 'Điểm danh đủ 10 buổi',
        'icon': 'event_available',
        'target_value': 10,
        'count_field': 'attendance_count',
    },
    {
        'code': 'attend_50',
        'title': 'Siêng năng',
        'description': 'Điểm danh đủ 50 buổi',
        'icon': 'event_note',
        'target_value': 50,
        'count_field': 'attendance_count',
    },
    {
        'code': 'classroom_5',
        'title': 'Khám phá',
        'description': 'Tham gia 5 lớp học',
        'icon': 'explore',
        'target_value': 5,
        'count_field': 'classrooms_joined_count',
    },
    {
        'code': 'classroom_10',
        'title': 'Đa lớp',
        'description': 'Tham gia 10 lớp học',
        'icon': 'dashboard',
        'target_value': 10,
        'count_field': 'classrooms_joined_count',
    },
    {
        'code': 'level_5',
        'title': 'Tập sự',
        'description': 'Đạt cấp 5',
        'icon': 'military_tech',
        'target_value': 5,
        'level_field': True,
    },
    {
        'code': 'level_10',
        'title': 'Cao thủ',
        'description': 'Đạt cấp 10',
        'icon': 'workspace_premium',
        'target_value': 10,
        'level_field': True,
    },
    {
        'code': 'level_20',
        'title': 'Huyền thoại',
        'description': 'Đạt cấp 20',
        'icon': 'emoji_events',
        'target_value': 20,
        'level_field': True,
    },
    {
        'code': 'streak_7',
        'title': '7 ngày liên tục',
        'description': 'Duy trì streak 7 ngày',
        'icon': 'local_fire_department',
        'target_value': 7,
        'streak_field': True,
    },
]


class AchievementService:
    def __init__(self):
        self.repo = AchievementRepository()

    def catalog(self):
        return ACHIEVEMENT_CATALOG

    def list_for_student(self, student_id):
        existing = {row.achievement_code: row for row in self.repo.list_by_student(student_id)}
        out = []
        for entry in ACHIEVEMENT_CATALOG:
            row = existing.get(entry['code'])
            out.append({
                'code': entry['code'],
                'title': entry['title'],
                'description': entry['description'],
                'icon': entry['icon'],
                'target_value': entry['target_value'],
                'current_value': int(getattr(row, 'current_value', 0) or 0) if row else 0,
                'progress_pct': int(getattr(row, 'progress_pct', 0) or 0) if row else 0,
                'is_unlocked': bool(getattr(row, 'is_unlocked', False)) if row else False,
                'unlocked_at': getattr(row, 'unlocked_at', None).isoformat() if row and getattr(row, 'unlocked_at', None) else None,
            })
        return out

    def _sync_progress(self, student_id, entry, value):
        if value <= 0:
            return None
        existing = self.repo.get(student_id, entry['code'])
        if existing and existing.is_unlocked:
            return None
        if existing is None:
            existing = self.repo.model.create(
                student_id=student_id,
                achievement_code=entry['code'],
                title=entry['title'],
                description=entry['description'],
                icon=entry['icon'],
                target_value=entry['target_value'],
                current_value=0,
                progress_pct=0,
                is_unlocked=False,
            )
        existing.current_value = value
        existing.progress_pct = min(100, int((value / max(1, entry['target_value'])) * 100))
        existing.updated_at = datetime.utcnow()
        existing.save()
        if value >= entry['target_value']:
            self._unlock(student_id, entry, existing)
        return existing

    def _unlock(self, student_id, entry, existing=None):
        row, was_new = self.repo.unlock(
            student_id,
            entry['code'],
            title=entry['title'],
            description=entry['description'],
            icon=entry['icon'],
            target_value=entry['target_value'],
            current_value=entry['target_value'],
            progress_pct=100,
        )
        if not was_new:
            return
        try:
            from features.notification.services.notification_service import NotificationService
            NotificationService().send_notification(
                target_uid=str(student_id),
                notify_type='ranking_achievement_unlocked',
                title=f'🏆 Mở khoá thành tựu: {entry["title"]}',
                content=entry['description'],
                metadata={
                    'achievement_code': entry['code'],
                    'icon': entry['icon'],
                },
            )
        except Exception as exc:
            logger.warning(f"[Achievement] notify failed: {exc}")

    def check_after_xp_event(self, student_id, event_type, student_xp=None):
        """Recompute progress for achievements that may have advanced."""
        for entry in ACHIEVEMENT_CATALOG:
            if entry.get('level_field'):
                level = int(getattr(student_xp, 'level', 0) or 0) if student_xp else 0
                self._sync_progress(student_id, entry, level)
            elif entry.get('streak_field'):
                streak = int(getattr(student_xp, 'streak_days', 0) or 0) if student_xp else 0
                self._sync_progress(student_id, entry, streak)
            elif entry.get('count_field'):
                count = int(getattr(student_xp, entry['count_field'], 0) or 0) if student_xp else 0
                self._sync_progress(student_id, entry, count)
