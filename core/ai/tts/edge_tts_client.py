"""
TTSClient — Text-to-Speech via edge-tts (Microsoft Edge TTS, free, no API key).

Requires internet. Voice defaults to Vietnamese female (vi-VN-HoaiMyNeural).
Set EDGE_TTS_VOICE in .env to override.

Usage:
    from core.ai.tts import TTSClient

    mp3_bytes = TTSClient.synthesize("Xin chào bạn")
"""

import asyncio
import io
import re
from typing import Optional

import edge_tts
from decouple import config

_DEFAULT_VOICE = config("EDGE_TTS_VOICE", default="vi-VN-HoaiMyNeural")
_MAX_CHARS = 3000
_RETRIES = 3


def _clean_text(text: str) -> str:
    """Strip markdown and normalize text so edge-tts always receives plain text."""
    text = re.sub(r'```[\s\S]*?```', '', text)        # code blocks
    text = re.sub(r'`[^`]*`', '', text)               # inline code
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)        # images
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # links → label
    text = re.sub(r'#{1,6}\s*', '', text)             # headings
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)  # bold/italic
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # bullets
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # numbered lists
    text = re.sub(r'>\s?', '', text)                  # blockquotes
    text = re.sub(r'[-—]{2,}', '.', text)             # dashes
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:_MAX_CHARS]


class TTSClient:

    @classmethod
    def synthesize(cls, text: str, voice: Optional[str] = None) -> bytes:
        """Convert text → MP3 bytes. Runs the async edge-tts call synchronously."""
        clean = _clean_text(text)
        if not clean:
            return b''
        return asyncio.run(cls._synthesize_async(clean, voice or _DEFAULT_VOICE))

    @staticmethod
    async def _synthesize_async(text: str, voice: str) -> bytes:
        last_exc = None
        for attempt in range(1, _RETRIES + 1):
            try:
                buf = io.BytesIO()
                communicate = edge_tts.Communicate(text, voice)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.write(chunk["data"])
                size = buf.tell()
                if size == 0:
                    raise RuntimeError("edge-tts returned 0 bytes")
                print(f"[TTS] synthesized {size} bytes (attempt {attempt}), voice={voice}")
                return buf.getvalue()
            except Exception as exc:
                last_exc = exc
                print(f"[TTS] attempt {attempt}/{_RETRIES} failed: {exc}")
                if attempt < _RETRIES:
                    await asyncio.sleep(1)
        raise RuntimeError(f"TTS failed after {_RETRIES} attempts: {last_exc}")
