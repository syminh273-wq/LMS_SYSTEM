from datetime import datetime
from uuid import UUID

from core.repositories.base_repository import BaseRepository
from features.ranking.models.achievement import StudentAchievement


class AchievementRepository(BaseRepository):
    model = StudentAchievement

    def get(self, student_id, code):
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
        except (ValueError, TypeError):
            return None
        return self.model.objects(student_id=sid, achievement_code=code).first()

    def list_by_student(self, student_id):
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
        except (ValueError, TypeError):
            return []
        return list(self.model.objects(student_id=sid))

    def unlock(self, student_id, code, **fields):
        existing = self.get(student_id, code)
        if existing:
            if existing.is_unlocked:
                return existing, False
            existing.is_unlocked = True
            existing.unlocked_at = datetime.utcnow()
            existing.progress_pct = 100
            for k, v in fields.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            existing.save()
            return existing, True
        defaults = {
            'is_unlocked': True,
            'unlocked_at': datetime.utcnow(),
            'progress_pct': 100,
        }
        defaults.update(fields)
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
        except (ValueError, TypeError):
            raise ValueError('Invalid student_id')
        defaults['student_id'] = sid
        defaults['achievement_code'] = code
        created = self.model.create(**defaults)
        return created, True

    def update_progress(self, student_id, code, current_value):
        existing = self.get(student_id, code)
        target = 1
        if existing:
            target = existing.target_value or 1
        else:
            return None
        existing.current_value = current_value
        existing.progress_pct = min(100, int((current_value / max(1, target)) * 100))
        existing.updated_at = datetime.utcnow()
        existing.save()
        return existing
