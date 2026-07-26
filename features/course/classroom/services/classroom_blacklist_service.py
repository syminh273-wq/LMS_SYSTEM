import uuid
from rest_framework.exceptions import PermissionDenied, NotFound

from features.course.classroom.models.teacher_blacklist import GLOBAL_SENTINEL
from features.course.classroom.repositories.teacher_blacklist_repository import TeacherBlacklistRepository


def _u(value):
    return uuid.UUID(str(value))


class ClassroomBlacklistService:
    def __init__(self):
        self.repo = TeacherBlacklistRepository()

    def is_blocked(self, classroom_uid, teacher_id, consumer_uid) -> bool:
        teacher_id = _u(teacher_id)
        consumer_uid = _u(consumer_uid)
        classroom_uid = _u(classroom_uid)

        if self.repo.get_classroom(teacher_id, classroom_uid, consumer_uid):
            return True
        if self.repo.get_global(teacher_id, consumer_uid):
            return True
        return False

    def add_classroom_block(self, classroom_uid, consumer_uid, added_by, reason=''):
        classroom = self._verify_ownership(classroom_uid, added_by)
        return self.repo.upsert_classroom_block(
            teacher_id=_u(classroom.teacher_id),
            classroom_uid=_u(classroom_uid),
            consumer_uid=_u(consumer_uid),
            reason=reason,
            added_by=_u(added_by),
        )

    def remove_classroom_block(self, classroom_uid, consumer_uid, removed_by):
        classroom = self._verify_ownership(classroom_uid, removed_by)
        entry = self.repo.get_classroom(_u(classroom.teacher_id), _u(classroom_uid), _u(consumer_uid))
        if not entry or entry.is_deleted:
            raise NotFound("Không tìm thấy mục trong danh sách chặn.")
        return self.repo.remove(entry)

    def list_classroom_blacklist(self, classroom_uid, requested_by):
        classroom = self._verify_ownership(classroom_uid, requested_by)
        return list(self.repo.list_for_teacher(_u(classroom.teacher_id), classroom_uid=_u(classroom_uid)))

    def add_global_block(self, teacher_id, consumer_uid, reason=''):
        return self.repo.upsert_global_block(
            teacher_id=_u(teacher_id),
            consumer_uid=_u(consumer_uid),
            reason=reason,
            added_by=_u(teacher_id),
        )

    def remove_global_block(self, teacher_id, consumer_uid):
        entry = self.repo.get_global(_u(teacher_id), _u(consumer_uid))
        if not entry or entry.is_deleted:
            raise NotFound("Không tìm thấy mục trong danh sách chặn toàn cầu.")
        return self.repo.remove(entry)

    def list_global_blacklist(self, teacher_id):
        return list(self.repo.list_for_teacher(_u(teacher_id), classroom_uid=GLOBAL_SENTINEL))

    def _verify_ownership(self, classroom_uid, teacher_id):
        from features.course.classroom.services.classroom_service import Service
        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(teacher_id):
            raise PermissionDenied("Chỉ giáo viên của lớp mới có quyền quản lý danh sách chặn.")
        return classroom
