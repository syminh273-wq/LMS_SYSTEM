"""
ChromaVectorService — thin wrapper around a ChromaDB persistent collection.
"""

import os

import chromadb
from django.conf import settings


class ChromaVectorService:
    def __init__(self, collection_name: str = "lms_store"):
        persist_dir = os.path.join(settings.BASE_DIR, "chroma_db")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, vector: list, doc_id: str, document: str = "", metadata: dict = None):
        self.collection.upsert(
            ids=[doc_id],
            embeddings=[vector],
            documents=[document],
            metadatas=[metadata or {}],
        )

    def query(self, vector: list, n_results: int = 5, where: dict = None) -> list:
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=n_results,
            where=where,
            include=["metadatas", "distances", "documents"],
        )
        out = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                dist = results["distances"][0][i]
                out.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": dist,
                    "score": 1 / (1 + dist),
                })
        return out

    def get_by_id(self, doc_id: str):
        result = self.collection.get(ids=[doc_id], include=["documents", "metadatas", "embeddings"])
        if result and result.get("ids"):
            return {
                "id": result["ids"][0],
                "document": result["documents"][0],
                "metadata": result["metadatas"][0],
                "embedding": result["embeddings"][0] if result.get("embeddings") else None,
            }
        return None

    def delete(self, doc_id: str):
        self.collection.delete(ids=[doc_id])

    def count(self) -> int:
        return self.collection.count()
