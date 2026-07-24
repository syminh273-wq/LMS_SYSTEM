"""
RAGService — thin compatibility wrapper around RAGPipeline.

Existing code that calls RAGService.process_document / get_context continues to work.
New code should use RAGPipeline directly for the full pipeline experience.
"""

import uuid

from core.ai.embeddings.services.multimodal_embedding_service import get_multimodal_service
from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.ai.vector_store.services.lance_vector_service import LanceVectorService

_TEXT_COLLECTION = RAGPipeline.DEFAULT_COLLECTION
_IMAGE_COLLECTION = "lms_image_store"

_pipeline = RAGPipeline()


class RAGService:

    # ── Text ──────────────────────────────────────────────────────────────────

    @classmethod
    def process_document(cls, file_path: str, metadata: dict = None) -> int:
        result = _pipeline.ingest(file_path=file_path, metadata=metadata)
        return result["chunks"]

    @classmethod
    def get_context(cls, query: str, k: int = 3, filter_meta: dict = None) -> str:
        hits = _pipeline.search(query, top_k=k, filter_meta=filter_meta)
        return "\n\n".join(h["document"] for h in hits)

    @classmethod
    def ask(cls, question: str, k: int = 3, filter_meta: dict = None) -> dict:
        return _pipeline.ask(question, top_k=k, filter_meta=filter_meta)

    @classmethod
    def ask_stream(cls, question: str, k: int = 3, filter_meta: dict = None):
        return _pipeline.ask_stream(question, top_k=k, filter_meta=filter_meta)

    @classmethod
    def update_document(cls, doc_id: str, new_text: str, metadata: dict = None):
        store = LanceVectorService(_TEXT_COLLECTION)
        embedder = _pipeline._get_embedder()
        vector = embedder.embed_query(new_text)
        store.add(vector=vector, doc_id=doc_id, document=new_text, metadata=metadata or {})
        print(f"[RAG] Updated {doc_id}")

    # ── Images ────────────────────────────────────────────────────────────────

    @classmethod
    def process_image(
        cls,
        image_source,
        description: str = "",
        metadata: dict = None,
        content_type: str = "image/png",
        doc_id: str = None,
    ) -> str:
        svc = get_multimodal_service()
        vector, img_hash = svc.get_image_embedding(image_source, content_type=content_type)
        unique_id = doc_id or f"img_{img_hash}"
        meta = {"image_hash": img_hash, **(metadata or {})}
        content = description or f"Image: {unique_id}"
        dim = len(vector)
        store = LanceVectorService(_IMAGE_COLLECTION, embed_dim=dim)
        store.add(vector=vector, doc_id=unique_id, document=content, metadata=meta)
        print(f"[RAG] Indexed image → {unique_id}")
        return unique_id

    @classmethod
    def delete_image(cls, classroom_id: str = None, resource_uid: str = None) -> int:
        """Delete image-store rows for a classroom or a specific resource."""
        where = {}
        if classroom_id:
            where["classroom_id"] = str(classroom_id)
        if resource_uid:
            where["resource_uid"] = str(resource_uid)
        if not where:
            return 0
        store = LanceVectorService(_IMAGE_COLLECTION)
        return store.delete_where(where)

    @classmethod
    def get_image_context(
        cls,
        image_source,
        k: int = 1,
        filter_meta: dict = None,
        content_type: str = "image/png",
        threshold: float = 0.5,
    ):
        svc = get_multimodal_service()
        try:
            vector, img_hash = svc.get_image_embedding(image_source, content_type=content_type)
        except Exception as exc:
            print(f"[RAG] Image embedding failed: {exc}")
            return "", []

        store = LanceVectorService(_IMAGE_COLLECTION)
        hash_id = f"img_{img_hash}"
        existing = store.get_by_id(hash_id)
        if existing:
            return existing["document"], [hash_id]

        results = store.query(vector, n_results=k, where=filter_meta)
        matched_docs, matched_ids = [], []
        for r in results:
            if r["distance"] <= threshold:
                matched_docs.append(r["document"])
                matched_ids.append(r["id"])
        return "\n\n".join(matched_docs), matched_ids
