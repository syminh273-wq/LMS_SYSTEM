"""
AIClient — unified AI gateway that switches backend based on AI_MODE env var.

AI_MODE=omni    → OmniRouteClient  (local OpenAI-compatible proxy, default)
AI_MODE=ollama  → OllamaClient     (local Ollama at localhost:11434)

Set AI_MODE in your .env. All other code should import AIClient instead of
a specific backend so switching providers needs only one env change.

Usage:
    from core.ai.llm import AIClient

    answer  = AIClient.chat_sync(messages)
    vectors = AIClient.embed_texts(["hello", "world"])
"""

from typing import Generator, List, Union

from decouple import config

_AI_MODE = config("AI_MODE", default="omni").lower()

if _AI_MODE == "ollama":
    from core.ai.llm.services.ollama_client import OllamaClient as _Backend
else:
    from core.ai.llm.services.omni_route_client import OmniRouteClient as _Backend


class AIClient:
    """
    Facade that delegates to OmniRouteClient or OllamaClient based on AI_MODE.
    Switch backends by changing AI_MODE in .env — no code changes needed.
    """

    TEXT_MODELS: List[str]      = _Backend.TEXT_MODELS
    VISION_MODELS: List[str]    = _Backend.VISION_MODELS
    TEXT_ID_MODELS: List[str]   = _Backend.TEXT_ID_MODELS
    VISION_ID_MODELS: List[str] = _Backend.VISION_ID_MODELS
    EMBED_MODEL: str            = _Backend.EMBED_MODEL

    @classmethod
    def chat_sync(
        cls,
        messages: List[dict],
        models: List[str] = None,
        timeout: int = 120,
    ) -> str:
        return _Backend.chat_sync(messages, models=models, timeout=timeout)

    @classmethod
    def chat_stream(
        cls,
        messages: List[dict],
        models: List[str] = None,
        timeout: int = 300,
    ) -> Generator[Union[str, tuple], None, None]:
        return _Backend.chat_stream(messages, models=models, timeout=timeout)

    @classmethod
    def embed_texts(
        cls,
        texts: List[str],
        model: str = None,
        timeout: int = 120,
    ) -> List[List[float]]:
        return _Backend.embed_texts(texts, model=model, timeout=timeout)

    @classmethod
    def embed_query(cls, text: str, model: str = None, timeout: int = 120) -> List[float]:
        return _Backend.embed_query(text, model=model, timeout=timeout)
