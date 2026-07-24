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

    def get_preview_folder(self, classroom_id):
        return self.filter(
            classroom_id=classroom_id,
            is_preview_only=True,
            is_deleted=False,
        ).first()

    def get_by_name_and_parent(self, classroom_id, name, parent_folder_id=None):
        qs = self.filter(
            classroom_id=classroom_id,
            name=name,
            is_deleted=False,
        )
        if parent_folder_id is None:
            qs = [f for f in qs if getattr(f, 'parent_folder_id', None) is None]
        else:
            parent_uuid = parent_folder_id if isinstance(parent_folder_id, UUID) else UUID(str(parent_folder_id))
            qs = [f for f in qs if getattr(f, 'parent_folder_id', None) == parent_uuid]
        return qs[0] if qs else None

    def count_preview_folders(self, classroom_id):
        return self.model.objects.filter(
            classroom_id=classroom_id,
            is_preview_only=True,
            is_deleted=False,
        ).count()

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
