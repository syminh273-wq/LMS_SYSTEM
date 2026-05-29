"""
Embedding backends for LMS_BACKEND.

OmniRouteEmbeddings — calls mistral-embed via OmniRoute (requires network proxy).
OllamaEmbeddings    — calls nomic-embed-text via local Ollama.
HashEmbeddings      — local n-gram hash, 1024 dims, zero deps, never rate-limited.

get_embedding_service() returns the backend selected by AI_MODE env var:
  AI_MODE=omni   → OmniRouteEmbeddings  (default)
  AI_MODE=ollama → OllamaEmbeddings
"""

import hashlib
from typing import List

import requests
from decouple import config
from langchain_core.embeddings import Embeddings

_AI_MODE = config("AI_MODE", default="omni").lower()


# ── OmniRoute ────────────────────────────────────────────────────────────────

class OmniRouteEmbeddings(Embeddings):
    """LangChain-compatible embeddings via OmniRoute (mistral-embed)."""

    def __init__(self, model: str = "mistral/mistral-embed", api_url: str = None):
        self.model = model
        self.api_url = api_url or (
            config("OMINIROUTE_BASE_URL", default="http://localhost:20128/v1") + "/embeddings"
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {config('OMINIROUTE_API_KEY', default='')}",
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


# ── Ollama ───────────────────────────────────────────────────────────────────

class OllamaEmbeddings(Embeddings):
    """LangChain-compatible embeddings via local Ollama /api/embed."""

    def __init__(self, model: str = None, base_url: str = None, batch_size: int = 16):
        self.model = model or config("OLLAMA_EMBED_MODEL", default="nomic-embed-text")
        self.api_url = (base_url or config("OLLAMA_BASE_URL", default="http://localhost:11434")) + "/api/embed"
        self.batch_size = batch_size

    def _call(self, texts: List[str]) -> List[List[float]]:
        # Increased timeout to 300s for slower machines/large batches
        resp = requests.post(
            self.api_url,
            json={"model": self.model, "input": texts},
            timeout=300,
        )
        if resp.status_code == 200:
            return resp.json()["embeddings"]
        raise RuntimeError(f"Ollama embed ({resp.status_code}): {resp.text}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Process documents in batches to avoid OOM or timeouts."""
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            all_embeddings.extend(self._call(batch))
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        return self._call([text])[0]


# ── Hash (local fallback) ─────────────────────────────────────────────────────

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


# ── Factory ───────────────────────────────────────────────────────────────────

_instance: Embeddings = None


def get_embedding_service() -> Embeddings:
    """Return the embedding service selected by AI_MODE."""
    global _instance
    if _instance is None:
        if _AI_MODE == "ollama":
            _instance = OllamaEmbeddings()
        else:
            _instance = OmniRouteEmbeddings()
    return _instance
