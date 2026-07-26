from datetime import datetime
from core.repositories.base_repository import BaseRepository
from features.course.classroom.models.teacher_blacklist import (
    GLOBAL_SENTINEL,
    TeacherBlacklist,
)


class TeacherBlacklistRepository(BaseRepository):
    model = TeacherBlacklist

    def list_for_teacher(self, teacher_id, classroom_uid=None):
        qs = self.filter(teacher_id=teacher_id, is_deleted=False)
        if classroom_uid is not None:
            return list(qs.filter(classroom_uid=classroom_uid))
        return list(qs)

    def list_for_classroom(self, classroom_uid):
        return list(
            self._qs()
            .filter(classroom_uid=classroom_uid, is_deleted=False)
            .allow_filtering()
        )

    def get(self, teacher_id, classroom_uid, consumer_uid):
        return self._qs().filter(
            teacher_id=teacher_id,
            classroom_uid=classroom_uid,
            consumer_uid=consumer_uid,
        ).first()

    def get_global(self, teacher_id, consumer_uid):
        return self.get(teacher_id, GLOBAL_SENTINEL, consumer_uid)

    def get_classroom(self, teacher_id, classroom_uid, consumer_uid):
        return self.get(teacher_id, classroom_uid, consumer_uid)

    def upsert_classroom_block(self, teacher_id, classroom_uid, consumer_uid, reason='', added_by=None):
        existing = self.get_classroom(teacher_id, classroom_uid, consumer_uid)
        if existing:
            existing.reason = reason
            existing.added_by = added_by
            existing.is_deleted = False
            existing.deleted_at = None
            existing.updated_at = datetime.utcnow()
            existing.save()
            return existing
        return TeacherBlacklist.create(
            teacher_id=teacher_id,
            classroom_uid=classroom_uid,
            consumer_uid=consumer_uid,
            reason=reason,
            added_by=added_by,
        )

    def upsert_global_block(self, teacher_id, consumer_uid, reason='', added_by=None):
        existing = self.get_global(teacher_id, consumer_uid)
        if existing:
            existing.reason = reason
            existing.added_by = added_by
            existing.is_deleted = False
            existing.deleted_at = None
            existing.updated_at = datetime.utcnow()
            existing.save()
            return existing
        return TeacherBlacklist.create(
            teacher_id=teacher_id,
            classroom_uid=GLOBAL_SENTINEL,
            consumer_uid=consumer_uid,
            reason=reason,
            added_by=added_by,
        )

    def remove(self, instance):
        instance.is_deleted = True
        instance.deleted_at = datetime.utcnow()
        instance.save()
        return instance
