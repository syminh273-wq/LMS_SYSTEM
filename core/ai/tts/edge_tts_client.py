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
from typing import Optional

import edge_tts
from decouple import config

_DEFAULT_VOICE = config("EDGE_TTS_VOICE", default="vi-VN-HoaiMyNeural")


class TTSClient:

    @classmethod
    def synthesize(cls, text: str, voice: Optional[str] = None) -> bytes:
        """Convert text → MP3 bytes. Runs the async edge-tts call synchronously."""
        return asyncio.run(cls._synthesize_async(text, voice or _DEFAULT_VOICE))

    @staticmethod
    async def _synthesize_async(text: str, voice: str) -> bytes:
        buf = io.BytesIO()
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        print(f"[TTS] synthesized {buf.tell()} bytes, voice={voice}")
        return buf.getvalue()
