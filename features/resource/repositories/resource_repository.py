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

    def get_by_owner_and_folder(self, owner_id, folder_id=None):
        qs = self.filter(owner_id=owner_id, is_deleted=False)
        if folder_id is None:
            # folder_id=None means "root level" -> keep only docs with no folder.
            return [r for r in qs if getattr(r, 'folder_id', None) is None]
        # Otherwise keep only docs belonging to the given folder.
        return [r for r in qs if getattr(r, 'folder_id', None) == folder_id]

    def find(self, uid):
        try:
            resource_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except ValueError as exc:
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.') from exc

        resource = self.model.objects(uid=resource_uid).first()

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
            'folder_id',
            'order_index',
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

        self.model.objects(uid=resource.uid).update(**update_data)

        return self.model.objects(uid=resource.uid).first()

    def bulk_update_positions(self, items):
        """items: iterable of {'uid', 'folder_id'?, 'order_index'}"""
        for item in items:
            try:
                uid = item['uid'] if isinstance(item['uid'], UUID) else UUID(str(item['uid']))
            except (ValueError, TypeError):
                continue
            update_kwargs = {'order_index': int(item.get('order_index', 0))}
            if 'folder_id' in item:
                update_kwargs['folder_id'] = item['folder_id'] if item['folder_id'] else None
            self.model.objects(uid=uid).update(**update_kwargs)

    def clear_folder_for_resources(self, folder_id):
        """When a folder is deleted, move all its children docs to root (folder_id = None)."""
        for r in self.filter(folder_id=folder_id, is_deleted=False):
            self.model.objects(uid=r.uid).update(folder_id=None, updated_at=datetime.now())
