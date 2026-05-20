"""
OmniRouteClient — central gateway for all AI calls in LMS_BACKEND.

OmniRoute is a local OpenAI-compatible proxy (default: http://localhost:20128).
Set OMINIROUTE_API_KEY and optionally OMINIROUTE_BASE_URL in your .env.

Usage:
    from core.ai.llm import OmniRouteClient

    # Sync
    answer = OmniRouteClient.chat_sync(messages, OmniRouteClient.TEXT_MODELS)

    # Streaming generator
    for chunk in OmniRouteClient.chat_stream(messages):
        if isinstance(chunk, tuple):
            signal, payload = chunk   # ('__FULL__', text) | ('__ERROR__', msg)
        else:
            print(chunk, end="")

    # Embeddings
    vectors = OmniRouteClient.embed_texts(["hello", "world"])
    vector  = OmniRouteClient.embed_query("search this")
"""

import json
import os
from typing import Generator, List, Union

import requests

_BASE_URL = os.environ.get("OMINIROUTE_BASE_URL", "http://localhost:20128/v1")
_CHAT_URL = f"{_BASE_URL}/chat/completions"
_EMBED_URL = f"{_BASE_URL}/embeddings"


def _key() -> str:
    return os.environ.get("OMINIROUTE_API_KEY", "")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }


class OmniRouteClient:
    """Stateless OmniRoute client. All methods are classmethods — no instance needed."""

    # Model combos in fallback order
    TEXT_MODELS: List[str]   = ["fast-text-combo", "text-smart-combo", "free-stack"]
    VISION_MODELS: List[str] = ["fast-vision-combo", "vision-ultra-combo", "free-stack"]
    TEXT_ID_MODELS: List[str]   = ["fast-text-combo", "text-smart-combo"]
    VISION_ID_MODELS: List[str] = ["fast-vision-combo", "vision-ultra-combo"]
    EMBED_MODEL: str = "mistral/mistral-embed"

    # ── Synchronous chat ─────────────────────────────────────────────────────

    @classmethod
    def chat_sync(
        cls,
        messages: List[dict],
        models: List[str] = None,
        timeout: int = 30,
    ) -> str:
        """Call LLM synchronously. Tries models in order, raises RuntimeError if all fail."""
        if models is None:
            models = cls.TEXT_MODELS

        last_error = ""
        for model in models:
            try:
                print(f"[OmniRoute] sync → {model}")
                resp = requests.post(
                    _CHAT_URL,
                    json={"model": model, "messages": messages, "stream": False},
                    headers=_headers(),
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    content = (
                        resp.json()
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    if content:
                        print(f"[OmniRoute] sync OK — {model}")
                        return content.strip()
                last_error = f"{model} → HTTP {resp.status_code}"
            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[OmniRoute] {last_error}")

        raise RuntimeError(f"All models failed. Last: {last_error}")

    # ── Streaming chat ───────────────────────────────────────────────────────

    @classmethod
    def chat_stream(
        cls,
        messages: List[dict],
        models: List[str] = None,
        timeout: int = 120,
    ) -> Generator[Union[str, tuple], None, None]:
        """
        Stream LLM response. Yields text chunks, then ('__FULL__', full_text)
        on success or ('__ERROR__', msg) if all models fail.
        """
        if models is None:
            models = cls.TEXT_MODELS

        last_error = ""
        for model in models:
            try:
                print(f"[OmniRoute] stream → {model}")
                resp = requests.post(
                    _CHAT_URL,
                    json={"model": model, "messages": messages, "stream": True},
                    headers=_headers(),
                    stream=True,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    buffer: List[str] = []
                    for raw in resp.iter_lines():
                        if not raw:
                            continue
                        line = raw.decode("utf-8")
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = (
                                json.loads(data_str)
                                .get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if chunk:
                                buffer.append(chunk)
                                yield chunk
                        except Exception:
                            pass
                    print(f"[OmniRoute] stream OK — {model}")
                    yield ("__FULL__", "".join(buffer))
                    return

                last_error = f"{model} → HTTP {resp.status_code}"
                print(f"[OmniRoute] {last_error}")

            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[OmniRoute] {last_error}")

        yield ("__ERROR__", last_error)

    # ── Embeddings ───────────────────────────────────────────────────────────

    @classmethod
    def embed_texts(
        cls,
        texts: List[str],
        model: str = None,
        timeout: int = 60,
    ) -> List[List[float]]:
        """Embed a list of texts via OmniRoute."""
        model = model or cls.EMBED_MODEL
        resp = requests.post(
            _EMBED_URL,
            json={"input": texts, "model": model},
            headers=_headers(),
            timeout=timeout,
        )
        if resp.status_code == 200:
            return [item["embedding"] for item in resp.json()["data"]]
        raise RuntimeError(f"Embed failed ({resp.status_code}): {resp.text}")

    @classmethod
    def embed_query(cls, text: str, model: str = None, timeout: int = 60) -> List[float]:
        """Embed a single query string."""
        return cls.embed_texts([text], model=model, timeout=timeout)[0]
