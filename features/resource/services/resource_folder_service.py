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
        """Return the nested folder tree for the classroom: each node is
        {'folder': ResourceFolder, 'children': [node, ...], 'docs': [Resource, ...]},
        sorted by order_index then name at every level."""
        folders = self.repository.get_by_classroom(classroom_id)
        docs = self.resource_repository.get_by_owner(classroom_id)
        return self.build_tree(folders, docs)

    def list_children(self, classroom_id, parent_folder_id=None):
        return self.repository.get_children(classroom_id, parent_folder_id)

    @staticmethod
    def build_tree(folders, docs):
        """Assemble folders + docs (flat, already filtered to one classroom)
        into a nested tree, each node carrying its own docs."""
        # Step 1: bucket docs by their folder_id (as string, so it matches the
        docs_by_folder = {}
        for doc in docs:
            folder_id = getattr(doc, 'folder_id', None)
            if folder_id is None:
                continue
            docs_by_folder.setdefault(str(folder_id), []).append(doc)

        # Step 2: create one flat node per folder first (dict keyed by uid string),
        nodes = {
            str(folder.uid): {'folder': folder, 'children': [], 'docs': docs_by_folder.get(str(folder.uid), [])}
            for folder in folders
        }

        # Step 3: wire each node into its parent's `children` list, or into
        roots = []
        for folder in folders:
            node = nodes[str(folder.uid)]
            parent_id = getattr(folder, 'parent_folder_id', None)
            parent_node = nodes.get(str(parent_id)) if parent_id else None
            (parent_node['children'] if parent_node else roots).append(node)

        # Step 4: sort every level (folders then their docs) by order_index,
        def sort_recursive(items):
            items.sort(key=lambda n: (n['folder'].order_index or 0, n['folder'].name))
            for item in items:
                item['docs'].sort(key=lambda d: (getattr(d, 'order_index', 0) or 0, d.name))
                sort_recursive(item['children'])

        sort_recursive(roots)
        return roots
