import uuid
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from features.course.classroom.repositories.classroom_blacklist_repository import ClassroomBlacklistRepository


class ClassroomBlacklistService:
    def __init__(self):
        self.repo = ClassroomBlacklistRepository()

    def is_blocked(self, classroom_uid, teacher_id, consumer_uid):
        """Return True if consumer is blocked at classroom level OR globally by teacher."""
        classroom_blocked = self.repo.is_blocked(
            scope_id=uuid.UUID(str(classroom_uid)),
            consumer_uid=uuid.UUID(str(consumer_uid)),
        )
        if classroom_blocked:
            return True
        global_blocked = self.repo.is_blocked(
            scope_id=uuid.UUID(str(teacher_id)),
            consumer_uid=uuid.UUID(str(consumer_uid)),
        )
        return global_blocked

    def add_classroom_block(self, classroom_uid, consumer_uid, added_by, reason=''):
        self._verify_ownership(classroom_uid, added_by)
        return self.repo.add(
            scope_id=uuid.UUID(str(classroom_uid)),
            consumer_uid=uuid.UUID(str(consumer_uid)),
            scope='classroom',
            added_by=uuid.UUID(str(added_by)),
            reason=reason,
        )

    def remove_classroom_block(self, classroom_uid, consumer_uid, removed_by):
        self._verify_ownership(classroom_uid, removed_by)
        entry = self.repo.remove(
            scope_id=uuid.UUID(str(classroom_uid)),
            consumer_uid=uuid.UUID(str(consumer_uid)),
        )
        if not entry:
            raise NotFound("Không tìm thấy mục trong danh sách chặn.")
        return entry

    def list_classroom_blacklist(self, classroom_uid, requested_by):
        self._verify_ownership(classroom_uid, requested_by)
        return list(self.repo.list_by_scope(uuid.UUID(str(classroom_uid))))

    def add_global_block(self, teacher_id, consumer_uid, reason=''):
        return self.repo.add(
            scope_id=uuid.UUID(str(teacher_id)),
            consumer_uid=uuid.UUID(str(consumer_uid)),
            scope='global',
            added_by=uuid.UUID(str(teacher_id)),
            reason=reason,
        )

    def remove_global_block(self, teacher_id, consumer_uid):
        entry = self.repo.remove(
            scope_id=uuid.UUID(str(teacher_id)),
            consumer_uid=uuid.UUID(str(consumer_uid)),
        )
        if not entry:
            raise NotFound("Không tìm thấy mục trong danh sách chặn toàn cầu.")
        return entry

    def list_global_blacklist(self, teacher_id):
        return list(self.repo.list_by_scope(uuid.UUID(str(teacher_id))))

    # ── Internal ──────────────────────────────────────────────────────────────

    def _verify_ownership(self, classroom_uid, teacher_id):
        from features.course.classroom.services.classroom_service import Service
        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(teacher_id):
            raise PermissionDenied("Chỉ giáo viên của lớp mới có quyền quản lý danh sách chặn.")
        return classroom
