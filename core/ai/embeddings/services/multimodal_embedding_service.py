"""
MultimodalEmbeddingService — image embeddings via Ollama vision model.

Flow: image → Ollama vision model describes it → embed the description → (vector, hash).
"""

import base64
import hashlib
from typing import Tuple

import requests
from decouple import config

_BASE_URL = config("OLLAMA_BASE_URL", default="http://localhost:11434")
_VISION_MODEL = config("OLLAMA_VISION_MODEL", default="llava")
_CHAT_URL = _BASE_URL + "/api/chat"


class MultimodalEmbeddingService:

    def get_image_embedding(
        self, image_source, content_type: str = "image/png"
    ) -> Tuple[list, str]:
        """
        Returns (embedding_vector, image_hash).
        image_source: file path (str), base64 string, or raw bytes.
        """
        if isinstance(image_source, bytes):
            raw = image_source
        elif isinstance(image_source, str):
            if image_source.startswith("data:") or len(image_source) > 512:
                b64 = image_source.split(",")[1] if "," in image_source else image_source
                raw = base64.b64decode(b64)
            else:
                with open(image_source, "rb") as f:
                    raw = f.read()
        else:
            raise ValueError("Unsupported image_source type")

        image_hash = hashlib.md5(raw).hexdigest()
        image_b64 = base64.b64encode(raw).decode("utf-8")

        description = self._describe_image(image_b64)
        vector = self._hash_embed(description)
        return vector, image_hash

    def _describe_image(self, image_b64: str) -> str:
        prompt_text = (
            "Describe this image in detail for semantic search. "
            "Include: main subject, key visual features, any text/labels visible, "
            "context and setting. Be specific and structured."
        )
        payload = {
            "model": _VISION_MODEL,
            "stream": False,
            "messages": [{
                "role": "user",
                "content": prompt_text,
                "images": [image_b64],
            }],
        }
        resp = requests.post(_CHAT_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()["message"]["content"]
        raise RuntimeError(f"Vision description failed ({resp.status_code}): {resp.text}")

    @staticmethod
    def _hash_embed(text: str, dims: int = 1024) -> list:
        from core.ai.embeddings.services.embedding_service import HashEmbeddings
        return HashEmbeddings(dims).embed_query(text)


_instance: MultimodalEmbeddingService = None


def get_multimodal_service() -> MultimodalEmbeddingService:
    global _instance
    if _instance is None:
        _instance = MultimodalEmbeddingService()
    return _instance
