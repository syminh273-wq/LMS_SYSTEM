"""
MultimodalEmbeddingService — image embeddings via vision model description.

AI_MODE=omni   → OmniRoute /v1/chat/completions  (OpenAI vision format)
AI_MODE=ollama → Ollama    /api/chat              (images field in message)

Flow: image → vision model describes it → embed the description → (vector, hash).
"""

import base64
import hashlib
from typing import Tuple

import requests
from decouple import config

_AI_MODE = config("AI_MODE", default="omni").lower()


class MultimodalEmbeddingService:
    def __init__(self):
        if _AI_MODE == "ollama":
            base = config("OLLAMA_BASE_URL", default="http://localhost:11434")
            self._chat_url = base + "/api/chat"
            self._vision_model = config("OLLAMA_VISION_MODEL", default="llava")
        else:
            base = config("OMINIROUTE_BASE_URL", default="http://localhost:20128/v1")
            self._chat_url = base + "/chat/completions"
            self._vision_model = "fast-vision-combo"

    def _headers(self) -> dict:
        if _AI_MODE == "ollama":
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {config('OMINIROUTE_API_KEY', default='')}",
            "Content-Type": "application/json",
        }

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

        description = self._describe_image(image_b64, content_type)
        vector = self._hash_embed(description)
        return vector, image_hash

    def _describe_image(self, image_b64: str, content_type: str) -> str:
        prompt_text = (
            "Describe this image in detail for semantic search. "
            "Include: main subject, key visual features, any text/labels visible, "
            "context and setting. Be specific and structured."
        )

        if _AI_MODE == "ollama":
            payload = {
                "model": self._vision_model,
                "stream": False,
                "messages": [{
                    "role": "user",
                    "content": prompt_text,
                    "images": [image_b64],
                }],
            }
        else:
            payload = {
                "model": self._vision_model,
                "stream": False,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image_b64}"}},
                    ],
                }],
            }

        resp = requests.post(self._chat_url, json=payload, headers=self._headers(), timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if _AI_MODE == "ollama":
                return data["message"]["content"]
            return data["choices"][0]["message"]["content"]
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
