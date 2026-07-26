from core.repositories.base_repository import BaseRepository
from features.course.classroom.models.teacher_global_blacklist import TeacherGlobalBlacklist


class TeacherGlobalBlacklistRepository(BaseRepository):
    model = TeacherGlobalBlacklist

    def get_entry(self, teacher_id, consumer_uid):
        return self.model.objects.filter(
            teacher_id=teacher_id, consumer_uid=consumer_uid
        ).first()

    def is_blocked(self, teacher_id, consumer_uid) -> bool:
        entry = self.get_entry(teacher_id, consumer_uid)
        return entry is not None and not entry.is_deleted

    def list_by_teacher(self, teacher_id):
        return self.model.objects.filter(teacher_id=teacher_id, is_deleted=False)

    def add(self, teacher_id, consumer_uid, reason=''):
        existing = self.get_entry(teacher_id, consumer_uid)
        if existing:
            if existing.is_deleted:
                existing.update(is_deleted=False, reason=reason)
            return existing
        return self.model.objects.create(
            teacher_id=teacher_id,
            consumer_uid=consumer_uid,
            added_by=teacher_id,
            reason=reason,
        )

    def remove(self, teacher_id, consumer_uid):
        entry = self.get_entry(teacher_id, consumer_uid)
        if entry and not entry.is_deleted:
            entry.update(is_deleted=True)
        return entry
