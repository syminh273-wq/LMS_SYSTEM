import os
import tempfile
import uuid as _uuid

from core.ai.rag.services.rag_pipeline import RAGPipeline
from features.resource.repositories.resource_repository import ResourceRepository
from features.resource.services.resource_service import ResourceService

# File types that can be parsed + indexed in LanceDB
_INDEXABLE_EXTENSIONS = {'.pdf', '.txt', '.md', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.json', '.xml', '.jpeg'}


class ClassroomDocService:
    _pipeline = RAGPipeline()

    def __init__(self):
        self._resource_service = ResourceService()
        self._resource_repo = ResourceRepository()

    # ── Public API ────────────────────────────────────────────────────────────

    def upload_and_index(self, classroom_uid: str, file_obj, section: str = ''):
        """
        Upload a document to R2 (tagged as classroom resource) and index
        its text content in the per-classroom LanceDB collection.
        """
        owner_id = _uuid.UUID(str(classroom_uid))

        result = self._resource_service.upload_resource(
            file_obj=file_obj,
            owner_id=owner_id,
            owner_type='classroom',
            metadata={'section': section},
        )
        if not result['success']:
            return result

        resource = result['data']

        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext in _INDEXABLE_EXTENSIONS:
            # Remove stale chunks for any previous upload of the same filename in this classroom
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

    def delete_doc(self, classroom_uid: str, resource_uid: str):
        """Soft-delete a document and remove its LanceDB chunks."""
        try:
            resource = self._resource_service.find(resource_uid)
            self._pipeline.delete_document({'resource_uid': resource_uid})
            self._resource_service.delete(resource)
            return {'success': True}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}
