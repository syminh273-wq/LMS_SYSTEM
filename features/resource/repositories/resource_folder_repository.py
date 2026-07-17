from uuid import UUID

from core.repositories.base_repository import BaseRepository
from features.resource.models.resource_folder import ResourceFolder


class ResourceFolderRepository(BaseRepository):
    model = ResourceFolder

    def get_by_classroom(self, classroom_id):
        return self.filter(classroom_id=classroom_id, is_deleted=False)

    def get_children(self, classroom_id, parent_folder_id):
        if parent_folder_id is None:
            return self.filter(
                classroom_id=classroom_id,
                parent_folder_id__isnull=True,
                is_deleted=False,
            )
        return self.filter(
            classroom_id=classroom_id,
            parent_folder_id=parent_folder_id,
            is_deleted=False,
        )

    def find(self, uid):
        try:
            folder_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except (ValueError, TypeError) as exc:
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.') from exc

        folder = self._qs().filter(uid=folder_uid).first()
        if not folder or folder.is_deleted:
            raise self.model.DoesNotExist(f'{self.model.__name__} not found.')
        return folder

    def soft_delete_recursive(self, folder):
        """Recursively soft-delete a folder and all its descendants."""
        folder.is_deleted = True
        folder.deleted_at = folder.deleted_at or folder.updated_at
        folder.save()

        children = self.filter(parent_folder_id=folder.uid, is_deleted=False)
        for child in children:
            self.soft_delete_recursive(child)
