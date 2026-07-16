"""
AIClient — unified AI gateway backed by local Ollama.

Set OLLAMA_BASE_URL / OLLAMA_MODEL / OLLAMA_EMBED_MODEL in your .env to customise.

Usage:
    from core.ai.llm import AIClient

    answer  = AIClient.chat_sync(messages)
    vectors = AIClient.embed_texts(["hello", "world"])
    result  = AIClient.chat_with_tools(messages, tools=[...])
"""

from typing import Generator, List, Union

from core.ai.llm.services.ollama_client import OllamaClient as _Backend


class AIClient:
    """Thin facade over OllamaClient."""

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
    def chat_sync_with_fallback(
        cls,
        messages: List[dict],
        validator=None,
        models: List[str] = None,
        timeout: int = 120,
    ) -> str:
        return _Backend.chat_sync_with_fallback(
            messages, validator=validator, models=models, timeout=timeout
        )

    @classmethod
    def chat_stream(
        cls,
        messages: List[dict],
        tools: List[dict] = None,
        models: List[str] = None,
        timeout: int = 300,
    ) -> Generator[Union[str, tuple], None, None]:
        return _Backend.chat_stream(messages, tools=tools, models=models, timeout=timeout)

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

    @classmethod
    def chat_with_tools(
        cls,
        messages: List[dict],
        tools: List[dict] = None,
        models: List[str] = None,
        timeout: int = 120,
    ) -> dict:
        """
        Call LLM with tool definitions. Returns {"content": str|None, "tool_calls": list|None}.
        """
        return _Backend.chat_with_tools(messages, tools=tools, models=models, timeout=timeout)
