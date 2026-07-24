import os
import tempfile
import uuid as _uuid

from core.ai.rag.services.rag_pipeline import RAGPipeline
from features.resource.repositories.resource_folder_repository import ResourceFolderRepository
from features.resource.repositories.resource_repository import ResourceRepository
from features.resource.services.resource_folder_service import ResourceFolderService
from features.resource.services.resource_service import ResourceService

# File types that can be parsed + indexed in LanceDB
_INDEXABLE_EXTENSIONS = {'.pdf', '.txt', '.md', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.json', '.xml', '.jpeg'}


class ClassroomDocService:
    _pipeline = RAGPipeline()

    def __init__(self):
        self._resource_service = ResourceService()
        self._resource_repo = ResourceRepository()
        self._folder_service = ResourceFolderService()
        self._folder_repo = ResourceFolderRepository()

    # ── Public API ────────────────────────────────────────────────────────────

    def upload_and_index(self, classroom_uid: str, file_obj, section: str = '', folder_id=None, order_index=0, exam_period=None):
        """
        Upload a document to R2 (tagged as classroom resource) and index
        its text content in the per-classroom LanceDB collection.

        If `exam_period` is provided and `folder_id` is not, auto-resolve the
        matching sub-folder under the classroom's "Bài kiểm tra" root folder.
        """
        owner_id = _uuid.UUID(str(classroom_uid))
        folder_uuid = _uuid.UUID(str(folder_id)) if folder_id else None

        if folder_uuid is None and exam_period:
            try:
                from features.resource.services.resource_folder_seed_service import ResourceFolderSeedService
                sub_folder = ResourceFolderSeedService().resolve_exam_sub_folder(
                    classroom_id=owner_id, exam_period=exam_period
                )
                if sub_folder is not None:
                    folder_uuid = sub_folder.uid
            except Exception as exc:
                print(f"[ClassroomDocService] Failed to resolve exam sub-folder: {exc}")

        metadata = {'section': section}
        if exam_period:
            metadata['exam_period'] = exam_period

        result = self._resource_service.upload_resource(
            file_obj=file_obj,
            owner_id=owner_id,
            owner_type='classroom',
            metadata=metadata,
            folder_id=folder_uuid,
            order_index=order_index,
        )
        if not result['success']:
            return result

        resource = result['data']

        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext in _INDEXABLE_EXTENSIONS:
            old_count = self._pipeline.delete_document({
                'classroom_id': str(classroom_uid),
                'doc_name': resource.name,
            })
            if old_count:
                print(f"[RAG] Removed {old_count} stale chunk(s) for '{resource.name}' before re-index")

            tmp_path = None
            try:
                file_obj.seek(0)
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    for chunk in file_obj.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                self._pipeline.ingest(
                    file_path=tmp_path,
                    metadata={
                        'classroom_id': str(classroom_uid),
                        'resource_uid': str(resource.uid),
                        'doc_name': resource.name,
                        'doc_url': resource.url,
                        'section': section,
                        'folder_id': str(folder_uuid) if folder_uuid else '',
                    },
                )
            except Exception as exc:
                import traceback
                traceback.print_exc()
                print(f"[ClassroomDocService] LanceDB index failed for {resource.name}: {exc}")
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                return {
                    'success': False,
                    'message': f'File đã upload lên R2 nhưng LanceDB indexing thất bại: {exc}',
                    'data': resource,
                }
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return {'success': True, 'data': resource}

    def list_docs(self, classroom_uid: str, section: str = None):
        """Return Resource records for this classroom, optionally filtered by section."""
        owner_id = _uuid.UUID(str(classroom_uid))
        qs = self._resource_repo.filter(
            owner_id=owner_id,
            owner_type='classroom',
            is_deleted=False,
        )
        if section is not None:
            qs = [r for r in qs if r.metadata.get('section') == section]
        return qs

    def list_folder(self, classroom_uid: str, folder_id=None):
        """Return docs in a given folder (None = root)."""
        owner_id = _uuid.UUID(str(classroom_uid))
        folder_uuid = _uuid.UUID(str(folder_id)) if folder_id else None
        return self._resource_repo.get_by_owner_and_folder(owner_id, folder_uuid)

    def list_tree(self, classroom_uid: str, consumer_id=None):
        """Return {folders: [...], docs_root: [...]} for the classroom.

        When a consumer_id is provided and the classroom is paid, restrict
        the result to the preview folder + its docs.
        """
        from features.course.classroom.repositories import Repository as ClassroomRepository
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository

        owner_id = _uuid.UUID(str(classroom_uid))
        preview_only = False
        if consumer_id is not None:
            try:
                classroom = ClassroomRepository().find(str(classroom_uid))
                if getattr(classroom, 'pricing_type', 'free') == 'paid':
                    member = ClassroomMemberRepository().get_paid_member(classroom_uid, consumer_id)
                    if member is None:
                        preview_only = True
            except Exception:
                pass

        if preview_only:
            preview_folder = self._folder_repo.get_preview_folder(owner_id)
            folders = [preview_folder] if preview_folder else []
            preview_folder_id = preview_folder.uid if preview_folder else None
            docs_root = self._resource_repo.get_by_owner_and_folder(owner_id, preview_folder_id)
            return {
                'folders': folders,
                'docs_root': [],
                'preview_only': True,
                'preview_folder': preview_folder,
            }

        folders = self._folder_service.list_tree(owner_id)
        root_docs = self._resource_repo.get_by_owner_and_folder(owner_id, None)
        return {
            'folders': folders,
            'docs_root': root_docs,
            'preview_only': False,
        }

    def get_preview_folder(self, classroom_uid: str):
        owner_id = _uuid.UUID(str(classroom_uid))
        return self._folder_repo.get_preview_folder(owner_id)

    def reorder(self, classroom_uid: str, items):
        """items: list of {uid, folder_id?, order_index?}.
        Verifies each item belongs to this classroom before update."""
        owner_id = _uuid.UUID(str(classroom_uid))
        for item in items:
            try:
                resource = self._resource_service.find(item['uid'])
            except Exception:
                continue
            if resource.owner_id != owner_id or resource.owner_type != 'classroom':
                continue
            update_kwargs = {'order_index': int(item.get('order_index', 0))}
            if 'folder_id' in item:
                f = item['folder_id']
                update_kwargs['folder_id'] = _uuid.UUID(str(f)) if f else None
            self._resource_service.repository.update(resource, **update_kwargs)
        return {'success': True}

    def delete_doc(self, classroom_uid: str, resource_uid: str):
        """Soft-delete a document and remove its LanceDB chunks."""
        try:
            resource = self._resource_service.find(resource_uid)
            self._pipeline.delete_document({'resource_uid': resource_uid})
            self._resource_service.delete(resource)
            return {'success': True}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}
