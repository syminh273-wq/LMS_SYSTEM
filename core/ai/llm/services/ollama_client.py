"""
OllamaClient — AI calls via local Ollama (http://localhost:11434).

Requires Ollama running locally. Set OLLAMA_BASE_URL / OLLAMA_MODEL /
OLLAMA_EMBED_MODEL in your .env to customise.

Used via AIClient — do not import directly.
"""

import json
from typing import Generator, List, Union

import requests
from decouple import config

_BASE_URL           = config("OLLAMA_BASE_URL",    default="http://localhost:11434")
_CHAT_URL           = f"{_BASE_URL}/api/chat"
_EMBED_URL          = f"{_BASE_URL}/api/embed"

_DEFAULT_MODEL        = config("OLLAMA_MODEL",        default="qwen2.5:3b")
_DEFAULT_FALLBACK_MODELS = [
    m.strip() for m in config(
        "OLLAMA_FALLBACK_MODELS",
        default="qwen2.5:7b,qwen2.5:14b,llama3.1:8b,mistral:7b",
    ).split(",") if m.strip()
]
_DEFAULT_TOOL_MODEL   = config("OLLAMA_TOOL_MODEL",   default="qwen2.5:3b")
_DEFAULT_EMBED_MODEL  = config("OLLAMA_EMBED_MODEL",  default="nomic-embed-text")
_DEFAULT_VISION_MODEL = config("OLLAMA_VISION_MODEL", default="llava")


def _build_text_model_chain() -> List[str]:
    chain = [_DEFAULT_MODEL]
    for m in _DEFAULT_FALLBACK_MODELS:
        if m and m != _DEFAULT_MODEL and m not in chain:
            chain.append(m)
    return chain


class OllamaClient:
    """Stateless Ollama client."""

    TEXT_MODELS: List[str]      = _build_text_model_chain()
    VISION_MODELS: List[str]    = [_DEFAULT_VISION_MODEL]
    TEXT_ID_MODELS: List[str]   = _build_text_model_chain()
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
                    json={"model": model, "messages": messages, "stream": False,
                          "options": {"temperature": 0, "num_ctx": 8192}},
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

    @classmethod
    def chat_sync_with_fallback(
        cls,
        messages: List[dict],
        validator=None,
        models: List[str] = None,
        timeout: int = 120,
    ) -> str:
        """
        Like chat_sync but if `validator(raw_text)` returns False,
        retry with the next model in the chain. Stops as soon as one
        model returns content that passes the validator.
        """
        if models is None:
            models = cls.TEXT_MODELS

        last_error = ""
        for idx, model in enumerate(models):
            try:
                print(f"[Ollama] sync_fb → {model} ({idx + 1}/{len(models)})")
                resp = requests.post(
                    _CHAT_URL,
                    json={"model": model, "messages": messages, "stream": False,
                          "options": {"temperature": 0, "num_ctx": 8192}},
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    content = resp.json().get("message", {}).get("content", "")
                    if content:
                        content = content.strip()
                        if validator is None or validator(content):
                            print(f"[Ollama] sync_fb OK — {model}")
                            return content
                        print(f"[Ollama] sync_fb {model} failed validator, trying next")
                        last_error = f"{model} → validator rejected output"
                        continue
                last_error = f"{model} → HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[Ollama] {last_error}")

        raise RuntimeError(f"All models failed. Last: {last_error}")

    # ── Vision chat (single image) ────────────────────────────────────────────

    @classmethod
    def chat_with_image(
        cls,
        messages: List[dict],
        image_b64: str,
        models: List[str] = None,
        timeout: int = 180,
    ) -> str:
        """
        Call a vision-capable Ollama model with a single image attached to the
        last user message. The image must be base64-encoded (without the
        ``data:...;base64,`` prefix). The vision model itself reads the image,
        so callers should not pass any image bytes inside ``messages``.

        Falls back through ``models`` in order. Default model is the configured
        ``OLLAMA_VISION_MODEL`` (llava).
        """
        if models is None:
            models = cls.VISION_MODELS

        if not image_b64:
            raise ValueError("image_b64 is required for chat_with_image")
        if not messages:
            raise ValueError("messages is required for chat_with_image")

        # Attach the image to the last user message (Ollama convention).
        attached = list(messages)
        last = dict(attached[-1])
        if last.get("role") != "user":
            raise ValueError("Last message must be role='user' for vision call")
        last["images"] = [image_b64]
        attached[-1] = last

        last_error = ""
        for model in models:
            try:
                print(f"[Ollama] vision → {model}")
                resp = requests.post(
                    _CHAT_URL,
                    json={"model": model, "messages": attached, "stream": False,
                          "options": {"temperature": 0, "num_ctx": 8192}},
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    content = resp.json().get("message", {}).get("content", "")
                    if content:
                        print(f"[Ollama] vision OK — {model}")
                        return content.strip()
                last_error = f"{model} → HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[Ollama] {last_error}")

        raise RuntimeError(f"All vision models failed. Last: {last_error}")

    # ── Streaming chat ───────────────────────────────────────────────────────

    @classmethod
    def chat_stream(
        cls,
        messages: List[dict],
        tools: List[dict] = None,
        models: List[str] = None,
        timeout: int = 300,
    ) -> Generator[Union[str, tuple], None, None]:
        if models is None:
            models = cls.TEXT_MODELS

        last_error = ""
        for model in models:
            try:
                print(f"[Ollama] stream → {model}")
                payload = {"model": model, "messages": messages, "stream": True,
                           "options": {"temperature": 0, "num_ctx": 8192}}
                if tools:
                    payload["tools"] = tools

                resp = requests.post(
                    _CHAT_URL,
                    json=payload,
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
                            msg = data.get("message", {})
                            
                            # Content chunk
                            chunk = msg.get("content", "")
                            if chunk:
                                buffer.append(chunk)
                                yield chunk
                            
                            # Tool calls (usually in the final chunk or specifically marked)
                            tcs = msg.get("tool_calls")
                            if tcs:
                                yield ("__TOOL_CALLS__", tcs)

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

    # ── Tool calling ─────────────────────────────────────────────────────────

    @classmethod
    def chat_with_tools(
        cls,
        messages: List[dict],
        tools: List[dict] = None,
        models: List[str] = None,
        timeout: int = 120,
    ) -> dict:
        """
        Call Ollama with tool definitions. Ollama supports OpenAI-compatible
        tools format since v0.2.8.
        Returns {"content": str|None, "tool_calls": list|None}.
        Uses OLLAMA_TOOL_MODEL (default: llama3.1) which supports tool calling.
        """
        if models is None:
            models = [_DEFAULT_TOOL_MODEL]

        last_error = ""
        for model in models:
            try:
                print(f"[Ollama] tool_call → {model}")
                payload: dict = {"model": model, "messages": messages, "stream": False,
                                 "options": {"temperature": 0, "num_ctx": 8192}}
                if tools:
                    payload["tools"] = tools
                resp = requests.post(_CHAT_URL, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    msg = resp.json().get("message", {})
                    print(f"[Ollama] tool_call OK — {model}")
                    return {
                        "content": msg.get("content"),
                        "tool_calls": msg.get("tool_calls"),
                    }
                last_error = f"{model} → HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[Ollama] {last_error}")
            except Exception as exc:
                last_error = f"{model} → {exc}"
                print(f"[Ollama] {last_error}")

        raise RuntimeError(f"All models failed. Last: {last_error}")
