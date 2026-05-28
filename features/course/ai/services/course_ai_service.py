"""
CourseAIService — RAG for classroom documents.

Permission rules
────────────────
  classroom_id passed → teacher must own the classroom (Classroom.teacher_id == user.uid)
  document_id  passed → teacher must own the resource  (Resource.owner_id  == user.uid)
                         OR the resource belongs to a classroom the teacher owns

Metadata stored in LanceDB during ingest
──────────────────────────────────────────
  classroom_id : str(UUID)   present when classroom_id was supplied at ingest
  resource_id  : str(UUID)   always present (the resource's uid)
"""

import os
import tempfile

import requests
from rest_framework.exceptions import NotFound, PermissionDenied

from core.ai.rag.services.rag_pipeline import RAGPipeline
from features.course.classroom.models.classroom import Classroom
from features.resource.repositories.resource_repository import ResourceRepository

_resource_repo = ResourceRepository()
_pipeline = RAGPipeline()

_INDEXABLE_TYPES = {"pdf", "txt", "md", "csv"}


class CourseAIService:

    # ─────────────────────────────────────────────────────────────────────────
    # Permission helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_classroom(classroom_id):
        classroom = Classroom.objects.filter(uid=classroom_id).allow_filtering().first()
        if not classroom:
            raise NotFound("Classroom not found.")
        return classroom

    @staticmethod
    def _get_resource(resource_id):
        try:
            return _resource_repo.find(resource_id)
        except Exception:
            raise NotFound("Resource not found.")

    @classmethod
    def _check_classroom_permission(cls, classroom_id, teacher_id):
        """Teacher must own the classroom."""
        classroom = cls._get_classroom(classroom_id)
        if str(classroom.teacher_id) != str(teacher_id):
            raise PermissionDenied("You do not have permission to access this classroom.")
        return classroom

    @classmethod
    def _check_document_permission(cls, resource_id, teacher_id):
        """Teacher must own the resource directly, or via a classroom they own."""
        resource = cls._get_resource(resource_id)
        if str(resource.owner_id) == str(teacher_id):
            return resource
        # Resource owned by a classroom → check that classroom belongs to teacher
        if resource.owner_type == "classroom":
            classroom = Classroom.objects.filter(
                uid=resource.owner_id
            ).allow_filtering().first()
            if classroom and str(classroom.teacher_id) == str(teacher_id):
                return resource
        raise PermissionDenied("You do not have permission to access this document.")

    # ─────────────────────────────────────────────────────────────────────────
    # Filter builder  (meta stored/queried in LanceDB)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_filter(classroom_id=None, document_id=None) -> dict:
        """
        Build the metadata filter dict for RAGPipeline.
        If both supplied the search is AND-filtered (both must match).
        If only one is supplied only that key is filtered.
        """
        f = {}
        if classroom_id:
            f["classroom_id"] = str(classroom_id)
        if document_id:
            f["resource_uid"] = str(document_id)
        return f or None

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def ask(
        cls,
        teacher_id,
        question: str,
        classroom_id=None,
        document_id=None,
        top_k: int = 3,
    ) -> dict:
        """
        Permission → build filter → similarity search → LLM answer.
        """
        # ── Permission checks ──────────────────────────────────────────────
        if classroom_id:
            cls._check_classroom_permission(classroom_id, teacher_id)
        if document_id:
            cls._check_document_permission(document_id, teacher_id)

        # ── RAG query ─────────────────────────────────────────────────────
        filter_meta = cls._build_filter(classroom_id, document_id)
        result = _pipeline.ask(question, top_k=top_k, filter_meta=filter_meta)
        return result

    @classmethod
    def ingest(
        cls,
        teacher_id,
        resource_id,
        classroom_id=None,
        document_id=None,
    ) -> dict:
        """
        Verify permissions → download resource → chunk → embed → store in LanceDB.

        document_id in query_params is treated as an additional metadata filter;
        resource_id in the request body is the file to ingest.
        """
        # ── Permission: classroom ──────────────────────────────────────────
        if classroom_id:
            cls._check_classroom_permission(classroom_id, teacher_id)

        # ── Permission: the resource being ingested ────────────────────────
        resource = cls._check_document_permission(resource_id, teacher_id)

        # ── Check file type ────────────────────────────────────────────────
        if resource.file_type.lower() not in _INDEXABLE_TYPES:
            return {
                "success": False,
                "message": f"File type '{resource.file_type}' is not supported for indexing. "
                           f"Supported types: {', '.join(sorted(_INDEXABLE_TYPES))}",
            }

        # ── Build metadata for LanceDB ─────────────────────────────────────
        metadata = {"resource_uid": str(resource.uid)}
        if classroom_id:
            metadata["classroom_id"] = str(classroom_id)
        if document_id:
            metadata["extra_document_id"] = str(document_id)

        # ── Download file to temp dir → ingest ────────────────────────────
        suffix = f".{resource.file_type.lower()}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            try:
                resp = requests.get(resource.url, timeout=60)
                resp.raise_for_status()
                tmp.write(resp.content)
            except Exception as exc:
                os.unlink(tmp_path)
                raise RuntimeError(f"Failed to download resource: {exc}") from exc

        try:
            result = _pipeline.ingest(file_path=tmp_path, metadata=metadata)
        finally:
            os.unlink(tmp_path)

        return {
            "success": True,
            "resource_uid": str(resource.uid),
            "resource_name": resource.name,
            "chunks": result["chunks"],
            "collection": result["collection"],
        }

    @classmethod
    def delete_index(
        cls,
        teacher_id,
        classroom_id=None,
        document_id=None,
    ) -> dict:
        """Remove all indexed chunks for a classroom or document."""
        if classroom_id:
            cls._check_classroom_permission(classroom_id, teacher_id)
        if document_id:
            cls._check_document_permission(document_id, teacher_id)

        filter_meta = cls._build_filter(classroom_id, document_id)
        if not filter_meta:
            raise PermissionDenied("Specify classroom_id or document_id to delete.")

        deleted = _pipeline.delete_document(filter_meta)
        return {"deleted_chunks": deleted, "filter": filter_meta}
