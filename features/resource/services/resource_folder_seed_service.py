from features.resource.repositories.resource_folder_repository import ResourceFolderRepository
from features.course.exam.constants import (
    EXAM_ROOT_FOLDER_NAME,
    EXAM_SUBFOLDER_NAMES,
    DOCS_ROOT_FOLDER_NAME,
    PREVIEW_ROOT_FOLDER_NAME,
)


class ResourceFolderSeedService:
    def __init__(self):
        self.repository = ResourceFolderRepository()

    def ensure_default_folders(self, classroom_id, teacher_id):
        from features.resource.services.resource_folder_service import ResourceFolderService
        folder_service = ResourceFolderService()

        preview, _ = folder_service.ensure_preview_folder(classroom_id, teacher_id)
        docs = self._ensure_root_folder(
            classroom_id=classroom_id,
            teacher_id=teacher_id,
            name=DOCS_ROOT_FOLDER_NAME,
            order_index=0,
        )
        exam_root = self._ensure_root_folder(
            classroom_id=classroom_id,
            teacher_id=teacher_id,
            name=EXAM_ROOT_FOLDER_NAME,
            order_index=1,
        )

        sub_folders = {}
        for idx, sub_name in enumerate(EXAM_SUBFOLDER_NAMES):
            sub_folders[sub_name] = self._ensure_child_folder(
                classroom_id=classroom_id,
                teacher_id=teacher_id,
                parent_folder=exam_root,
                name=sub_name,
                order_index=idx,
            )

        return {
            'preview': preview,
            'docs': docs,
            'exam_root': exam_root,
            'exam_sub_folders': sub_folders,
        }

    def _ensure_root_folder(self, classroom_id, teacher_id, name, order_index=0):
        existing = self.repository.get_by_name_and_parent(classroom_id, name, None)
        if existing:
            return existing
        return self.repository.create(
            classroom_id=classroom_id,
            name=name,
            parent_folder_id=None,
            owner_id=teacher_id,
            order_index=order_index,
            color=None,
            is_preview_only=False,
        )

    def _ensure_child_folder(self, classroom_id, teacher_id, parent_folder, name, order_index=0):
        existing = self.repository.get_by_name_and_parent(classroom_id, name, parent_folder.uid)
        if existing:
            return existing
        return self.repository.create(
            classroom_id=classroom_id,
            name=name,
            parent_folder_id=parent_folder.uid,
            owner_id=teacher_id,
            order_index=order_index,
            color=None,
            is_preview_only=False,
        )

    def resolve_exam_sub_folder(self, classroom_id, exam_period):
        if not exam_period:
            return None
        from features.course.exam.constants import EXAM_PERIOD_TO_FOLDER_NAME
        folder_name = EXAM_PERIOD_TO_FOLDER_NAME.get(exam_period)
        if not folder_name:
            return None
        exam_root = self.repository.get_by_name_and_parent(classroom_id, EXAM_ROOT_FOLDER_NAME, None)
        if not exam_root:
            return None
        return self.repository.get_by_name_and_parent(classroom_id, folder_name, exam_root.uid)
