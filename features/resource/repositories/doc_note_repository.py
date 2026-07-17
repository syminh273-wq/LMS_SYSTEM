from uuid import UUID

from core.repositories.base_repository import BaseRepository
from features.resource.models.doc_note import DocNote


class DocNoteRepository(BaseRepository):
    model = DocNote

    def get_for_resource(self, resource_uid):
        try:
            ruid = resource_uid if isinstance(resource_uid, UUID) else UUID(str(resource_uid))
        except (ValueError, TypeError):
            return []
        return self.filter(resource_uid=ruid, is_deleted=False)

    def get_for_student_in_classroom(self, student_id, classroom_id):
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
            cid = classroom_id if isinstance(classroom_id, UUID) else UUID(str(classroom_id))
        except (ValueError, TypeError):
            return []
        qs = self.model.objects(student_id=sid, classroom_id=cid).allow_filtering()
        return [n for n in qs if not getattr(n, 'is_deleted', False)]

    def get_for_student_resource(self, resource_uid, student_id):
        try:
            ruid = resource_uid if isinstance(resource_uid, UUID) else UUID(str(resource_uid))
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
        except (ValueError, TypeError):
            return []
        qs = self.model.objects(resource_uid=ruid, student_id=sid).allow_filtering()
        return [n for n in qs if not getattr(n, 'is_deleted', False)]

    def find(self, uid):
        try:
            note_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except (ValueError, TypeError) as exc:
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.') from exc
        instance = self._qs().filter(uid=note_uid).first()
        if not instance or getattr(instance, 'is_deleted', False):
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.')
        return instance
