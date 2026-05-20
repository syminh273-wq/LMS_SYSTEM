"""
RAGService — Retrieval-Augmented Generation for LMS course materials.

Supports:
  - process_document(file_path, metadata)  — chunk & index a PDF/TXT into ChromaDB
  - get_context(query, k, filter)          — retrieve relevant chunks for a query
  - process_image(image_path, ...)         — index an image by its vision description
  - get_image_context(image_path, ...)     — find similar images
  - update_document(doc_id, new_text)      — correct/update a stored entry
"""

import os
import uuid

from django.conf import settings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ai.embeddings.services.embedding_service import get_embedding_service
from core.ai.embeddings.services.multimodal_embedding_service import get_multimodal_service


_CHROMA_DIR = os.path.join(settings.BASE_DIR, "chroma_db")


class RAGService:
    """Stateless RAG service backed by ChromaDB."""

    # ── Text document indexing ────────────────────────────────────────────────

    @classmethod
    def process_document(cls, file_path: str, metadata: dict = None):
        """
        Chunk a PDF or TXT file and store in ChromaDB.
        metadata keys are attached to every chunk (e.g. classroom_id, resource_id).
        """
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        loader = PyPDFLoader(file_path) if file_path.endswith(".pdf") else TextLoader(file_path)
        docs = loader.load()

        if metadata:
            for doc in docs:
                doc.metadata.update(metadata)

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)

        Chroma.from_documents(
            documents=chunks,
            embedding=get_embedding_service(),
            persist_directory=_CHROMA_DIR,
        )
        print(f"[RAG] Indexed {len(chunks)} chunks from {file_path}")
        return len(chunks)

    @classmethod
    def get_context(cls, query: str, k: int = 3, filter_meta: dict = None) -> str:
        """
        Retrieve the top-k relevant document chunks for a query.
        Returns concatenated text ready to inject as a system message.
        """
        if not os.path.exists(_CHROMA_DIR):
            return ""
        store = Chroma(
            persist_directory=_CHROMA_DIR,
            embedding_function=get_embedding_service(),
        )
        results = store.similarity_search(query, k=k, filter=filter_meta or None)
        return "\n\n".join(doc.page_content for doc in results)

    # ── Image indexing ────────────────────────────────────────────────────────

    @classmethod
    def process_image(
        cls,
        image_source,
        description: str = "",
        metadata: dict = None,
        content_type: str = "image/png",
        doc_id: str = None,
    ) -> str:
        """
        Generate a vision embedding for an image and store it in ChromaDB.
        Returns the stored doc_id.
        """
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        svc = get_multimodal_service()
        vector, img_hash = svc.get_image_embedding(image_source, content_type=content_type)

        store = Chroma(
            persist_directory=_CHROMA_DIR,
            embedding_function=get_embedding_service(),
        )

        unique_id = doc_id or f"img_{img_hash}"
        meta = {"image_hash": img_hash, **(metadata or {})}
        content = description or f"Image: {unique_id}"

        store._collection.upsert(
            ids=[unique_id],
            embeddings=[vector],
            documents=[content],
            metadatas=[meta],
        )
        print(f"[RAG] Indexed image → {unique_id}")
        return unique_id

    @classmethod
    def get_image_context(
        cls,
        image_source,
        k: int = 1,
        filter_meta: dict = None,
        content_type: str = "image/png",
        threshold: float = 0.5,
    ):
        """
        Find similar images in ChromaDB.
        Returns (context_text, list_of_matched_ids).
        """
        if not os.path.exists(_CHROMA_DIR):
            return "", []

        svc = get_multimodal_service()
        try:
            vector, img_hash = svc.get_image_embedding(image_source, content_type=content_type)
        except Exception as exc:
            print(f"[RAG] Image embedding failed: {exc}")
            return "", []

        store = Chroma(
            persist_directory=_CHROMA_DIR,
            embedding_function=get_embedding_service(),
        )

        hash_id = f"img_{img_hash}"
        try:
            existing = store._collection.get(ids=[hash_id], include=["documents"])
            if existing and existing.get("ids"):
                return existing["documents"][0], [hash_id]
        except Exception:
            pass

        results = store._collection.query(
            query_embeddings=[vector],
            n_results=k,
            where=filter_meta or None,
            include=["documents", "distances"],
        )
        matched_docs, matched_ids = [], []
        if results and results.get("documents"):
            for doc, dist, doc_id in zip(
                results["documents"][0],
                results["distances"][0],
                results.get("ids", [[]])[0],
            ):
                if dist <= threshold:
                    matched_docs.append(doc)
                    matched_ids.append(doc_id)

        return "\n\n".join(matched_docs), matched_ids

    # ── Update ────────────────────────────────────────────────────────────────

    @classmethod
    def update_document(cls, doc_id: str, new_text: str, metadata: dict = None):
        """Update the stored text (and optionally metadata) for an existing entry."""
        if not os.path.exists(_CHROMA_DIR):
            return
        store = Chroma(
            persist_directory=_CHROMA_DIR,
            embedding_function=get_embedding_service(),
        )
        existing = store._collection.get(ids=[doc_id], include=["embeddings"])
        old_embs = existing.get("embeddings") if existing else None

        update_meta = metadata or {}
        if old_embs and len(old_embs) > 0:
            store._collection.upsert(
                ids=[doc_id],
                embeddings=list(old_embs),
                documents=[new_text],
                metadatas=[update_meta],
            )
        else:
            store._collection.update(
                ids=[doc_id],
                documents=[new_text],
                metadatas=[update_meta],
            )
        print(f"[RAG] Updated {doc_id}")
