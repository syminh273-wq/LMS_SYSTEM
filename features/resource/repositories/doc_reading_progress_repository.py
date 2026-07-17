from datetime import datetime
from uuid import UUID

from cassandra.cqlengine import query
from core.repositories.base_repository import BaseRepository
from features.resource.models.doc_reading_progress import DocReadingProgress


class DocReadingProgressRepository(BaseRepository):
    model = DocReadingProgress

    def get_for_student(self, classroom_id, student_id):
        return list(self.filter(classroom_id=classroom_id, student_id=student_id, is_deleted=False))

    def get_for_student_resource(self, classroom_id, student_id, resource_uid):
        try:
            ruid = resource_uid if isinstance(resource_uid, UUID) else UUID(str(resource_uid))
        except (ValueError, TypeError):
            return None
        instance = (
            self.model.objects(classroom_id=classroom_id, student_id=student_id, resource_uid=ruid)
            .allow_filtering()
            .first()
        )
        if not instance or getattr(instance, 'is_deleted', False):
            return None
        return instance

    def get_for_resource_all_students(self, classroom_id, resource_uid):
        try:
            ruid = resource_uid if isinstance(resource_uid, UUID) else UUID(str(resource_uid))
        except (ValueError, TypeError):
            return []
        qs = (
            self.model.objects(classroom_id=classroom_id, resource_uid=ruid)
            .allow_filtering()
        )
        return [r for r in qs if not getattr(r, 'is_deleted', False)]

    def upsert(self, classroom_id, student_id, resource_uid, **data):
        try:
            ruid = resource_uid if isinstance(resource_uid, UUID) else UUID(str(resource_uid))
        except (ValueError, TypeError):
            raise ValueError('Invalid resource_uid')
        cid = UUID(str(classroom_id))
        sid = UUID(str(student_id))

        instance = self.get_for_student_resource(cid, sid, ruid)
        if instance is None:
            data.setdefault('read_progress', 0)
            data.setdefault('is_completed', False)
            data['classroom_id'] = cid
            data['student_id'] = sid
            data['resource_uid'] = ruid
            return self.create(**data)
        update_data = {k: v for k, v in data.items() if k in {'read_progress', 'is_completed', 'last_opened_at'}}
        update_data['updated_at'] = datetime.now()
        if update_data.get('is_completed') and not getattr(instance, 'is_completed', False):
            update_data['completed_at'] = datetime.now()
        for k, v in update_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance
