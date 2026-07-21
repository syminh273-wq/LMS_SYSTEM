from uuid import UUID

from core.services.base_service import BaseService
from features.resource.repositories.resource_folder_repository import ResourceFolderRepository
from features.resource.repositories.resource_repository import ResourceRepository


class ResourceFolderService(BaseService):
    def __init__(self):
        self.repository = ResourceFolderRepository()
        self.resource_repository = ResourceRepository()

    def create_folder(self, classroom_id, teacher_id, name, parent_folder_id=None, order_index=0, color=None, is_preview_only=False):
        if is_preview_only:
            existing = self.repository.count_preview_folders(classroom_id)
            if existing > 0:
                raise ValueError('Lớp học này đã có Preview folder. Mỗi lớp chỉ được tạo tối đa 1 Preview folder.')
        data = {
            'classroom_id': UUID(str(classroom_id)),
            'name': name,
            'parent_folder_id': UUID(str(parent_folder_id)) if parent_folder_id else None,
            'owner_id': UUID(str(teacher_id)),
            'order_index': int(order_index or 0),
            'color': color or None,
            'is_preview_only': bool(is_preview_only),
        }
        return self.repository.create(**data)

    def rename_folder(self, folder, new_name):
        return self.repository.update(folder, name=new_name)

    def move_folder(self, folder, new_parent_id):
        new_parent_uuid = UUID(str(new_parent_id)) if new_parent_id else None
        if new_parent_uuid and new_parent_uuid == folder.uid:
            raise ValueError('Folder cannot be its own parent.')
        return self.repository.update(folder, parent_folder_id=new_parent_uuid)

    def ensure_preview_folder(self, classroom_id, teacher_id):
        existing = self.repository.get_preview_folder(classroom_id)
        if existing:
            return existing, False
        folder = self.create_folder(
            classroom_id=classroom_id,
            teacher_id=teacher_id,
            name='Preview',
            order_index=-1,
            is_preview_only=True,
        )
        return folder, True

    def delete_folder(self, folder):
        """Soft-delete folder + descendants, move docs to root."""
        self.resource_repository.clear_folder_for_resources(folder.uid)
        self.repository.soft_delete_recursive(folder)

    def list_tree(self, classroom_id):
        """Return flat list of all non-deleted folders in the classroom,
        caller (frontend) builds the tree view."""
        return self.repository.get_by_classroom(classroom_id)

    def list_children(self, classroom_id, parent_folder_id=None):
        return self.repository.get_children(classroom_id, parent_folder_id)
