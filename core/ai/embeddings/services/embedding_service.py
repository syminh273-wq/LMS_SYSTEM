"""
Two embedding backends for LMS_BACKEND:

OmniRouteEmbeddings — calls mistral/mistral-embed via OmniRoute (requires network).
HashEmbeddings      — local n-gram hash, 1024 dims, zero deps, never rate-limited.

get_embedding_service() returns the default singleton (HashEmbeddings for stability).
"""

import hashlib
import os
from typing import List

import requests
from langchain_core.embeddings import Embeddings


class OmniRouteEmbeddings(Embeddings):
    """LangChain-compatible embeddings via OmniRoute (mistral-embed)."""

    def __init__(self, model: str = "mistral/mistral-embed", api_url: str = None):
        self.model = model
        self.api_url = api_url or (
            os.environ.get("OMINIROUTE_BASE_URL", "http://localhost:20128/v1") + "/embeddings"
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {os.environ.get('OMINIROUTE_API_KEY', '')}",
            "Content-Type": "application/json",
        }

    def _call(self, texts: List[str]) -> List[List[float]]:
        resp = requests.post(
            self.api_url,
            json={"input": texts, "model": self.model},
            headers=self._headers(),
            timeout=60,
        )
        if resp.status_code == 200:
            return [item["embedding"] for item in resp.json()["data"]]
        raise RuntimeError(f"OmniRoute embed ({resp.status_code}): {resp.text}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._call(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._call([text])[0]


class HashEmbeddings(Embeddings):
    """
    Local bi+tri-gram + word hash embedding.
    1024-dim, L2-normalised. Stable vector space, no network deps.
    """

    def __init__(self, dims: int = 1024):
        self.dims = dims

    def _encode(self, text: str) -> List[float]:
        text = str(text).lower().strip()
        if not text:
            return [0.0] * self.dims
        vec = [0.0] * self.dims
        for n in (2, 3):
            if len(text) >= n:
                for i in range(len(text) - n + 1):
                    idx = int(hashlib.md5(text[i: i + n].encode()).hexdigest(), 16) % self.dims
                    vec[idx] += 1.0
        for word in text.split():
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims
            vec[idx] += 3.0
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec] if norm else vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._encode(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._encode(text)


_instance: Embeddings = None


def get_embedding_service() -> HashEmbeddings:
    """Return the shared embedding service singleton."""
    global _instance
    if _instance is None:
        _instance = HashEmbeddings()
    return _instance
