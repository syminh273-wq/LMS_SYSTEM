"""
OllamaClient — AI calls via local Ollama (http://localhost:11434).

Requires Ollama running locally. Set OLLAMA_BASE_URL / OLLAMA_MODEL /
OLLAMA_EMBED_MODEL in your .env to customise.

Same interface as OmniRouteClient so they are interchangeable via AIClient.
"""

import json
from typing import Generator, List, Union

import requests
from decouple import config

_BASE_URL           = config("OLLAMA_BASE_URL",    default="http://localhost:11434")
_CHAT_URL           = f"{_BASE_URL}/api/chat"
_EMBED_URL          = f"{_BASE_URL}/api/embed"

_DEFAULT_MODEL        = config("OLLAMA_MODEL",        default="llama3")
_DEFAULT_EMBED_MODEL  = config("OLLAMA_EMBED_MODEL",  default="nomic-embed-text")
_DEFAULT_VISION_MODEL = config("OLLAMA_VISION_MODEL", default="llava")


class OllamaClient:
    """Stateless Ollama client. Same interface as OmniRouteClient."""

    TEXT_MODELS: List[str]      = [_DEFAULT_MODEL]
    VISION_MODELS: List[str]    = [_DEFAULT_VISION_MODEL]
    TEXT_ID_MODELS: List[str]   = [_DEFAULT_MODEL]
    VISION_ID_MODELS: List[str] = [_DEFAULT_VISION_MODEL]
    EMBED_MODEL: str            = _DEFAULT_EMBED_MODEL

    # ── Synchronous chat ─────────────────────────────────────────────────────

    @classmethod
    def chat_sync(
        cls,
        messages: List[dict],
        models: List[str] = None,
        timeout: int = 120,
    ) -> str:
        if models is None:
            models = cls.TEXT_MODELS

        last_error = ""
        for model in models:
            try:
                print(f"[Ollama] sync → {model}")
                resp = requests.post(
                    _CHAT_URL,
                    json={"model": model, "messages": messages, "stream": False},
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    content = resp.json().get("message", {}).get("content", "")
                    if content:
                        print(f"[Ollama] sync OK — {model}")
                        return content.strip()
                last_error = f"{model} → HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[Ollama] {last_error}")

        raise RuntimeError(f"All models failed. Last: {last_error}")

    # ── Streaming chat ───────────────────────────────────────────────────────

    @classmethod
    def chat_stream(
        cls,
        messages: List[dict],
        models: List[str] = None,
        timeout: int = 300,
    ) -> Generator[Union[str, tuple], None, None]:
        if models is None:
            models = cls.TEXT_MODELS

        last_error = ""
        for model in models:
            try:
                print(f"[Ollama] stream → {model}")
                resp = requests.post(
                    _CHAT_URL,
                    json={"model": model, "messages": messages, "stream": True},
                    stream=True,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    buffer: List[str] = []
                    for raw in resp.iter_lines():
                        if not raw:
                            continue
                        try:
                            data = json.loads(raw.decode("utf-8"))
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                buffer.append(chunk)
                                yield chunk
                            if data.get("done"):
                                break
                        except Exception:
                            pass
                    print(f"[Ollama] stream OK — {model}")
                    yield ("__FULL__", "".join(buffer))
                    return

                last_error = f"{model} → HTTP {resp.status_code}"
                print(f"[Ollama] {last_error}")

            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[Ollama] {last_error}")

        yield ("__ERROR__", last_error)

    # ── Embeddings ───────────────────────────────────────────────────────────

    @classmethod
    def embed_texts(
        cls,
        texts: List[str],
        model: str = None,
        timeout: int = 120,
    ) -> List[List[float]]:
        """Embed a list of texts via Ollama /api/embed (supports batch)."""
        model = model or cls.EMBED_MODEL
        resp = requests.post(
            _EMBED_URL,
            json={"model": model, "input": texts},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()["embeddings"]
        raise RuntimeError(f"Embed failed ({resp.status_code}): {resp.text}")

    @classmethod
    def embed_query(cls, text: str, model: str = None, timeout: int = 120) -> List[float]:
        return cls.embed_texts([text], model=model, timeout=timeout)[0]
