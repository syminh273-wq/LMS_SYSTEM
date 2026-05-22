from datetime import datetime
from uuid import UUID

from core.repositories.base_repository import BaseRepository
from features.resource.models.resource import Resource


class ResourceRepository(BaseRepository):
    model = Resource

    def get_by_owner(self, owner_id):
        return self.filter(owner_id=owner_id, is_deleted=False)

    def get_by_type(self, file_type):
        return self.filter(file_type=file_type, is_deleted=False)

    def find(self, uid):
        try:
            resource_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except ValueError as exc:
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.') from exc

        resource = self.model.objects(bucket=0, uid=resource_uid).first()

        if not resource or resource.is_deleted:
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.')

        return resource

    def update(self, resource, **data):
        allowed_fields = {
            'name',
            'file_type',
            'url',
            'size',
            'owner_id',
            'owner_type',
            'metadata',
            'is_deleted',
            'deleted_at',
        }
        update_data = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }
        update_data['updated_at'] = datetime.now()

        self.model.objects(bucket=0, uid=resource.uid).update(**update_data)

        return self.model.objects(bucket=0, uid=resource.uid).first()
