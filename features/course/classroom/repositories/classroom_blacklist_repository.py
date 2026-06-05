from core.repositories.base_repository import BaseRepository
from features.course.classroom.models.classroom_blacklist import ClassroomBlacklist


class ClassroomBlacklistRepository(BaseRepository):
    model = ClassroomBlacklist

    def get_entry(self, scope_id, consumer_uid):
        return self.model.objects.filter(
            scope_id=scope_id, consumer_uid=consumer_uid
        ).first()

    def is_blocked(self, scope_id, consumer_uid):
        entry = self.get_entry(scope_id, consumer_uid)
        return entry is not None and not entry.is_deleted

    def list_by_scope(self, scope_id):
        return self.model.objects.filter(scope_id=scope_id, is_deleted=False)

    def add(self, scope_id, consumer_uid, scope, added_by, reason=''):
        existing = self.get_entry(scope_id, consumer_uid)
        if existing:
            if existing.is_deleted:
                existing.update(is_deleted=False, reason=reason)
            return existing
        return self.model.objects.create(
            scope_id=scope_id,
            consumer_uid=consumer_uid,
            scope=scope,
            added_by=added_by,
            reason=reason,
        )

    def remove(self, scope_id, consumer_uid):
        entry = self.get_entry(scope_id, consumer_uid)
        if entry and not entry.is_deleted:
            entry.update(is_deleted=True)
        return entry
