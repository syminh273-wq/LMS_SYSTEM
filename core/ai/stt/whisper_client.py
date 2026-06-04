"""
WhisperClient — local Speech-to-Text via faster-whisper.

Model `tiny` (~75 MB) is downloaded once to ~/.cache/huggingface/ on first use.
Runs entirely offline on CPU with int8 quantisation — no API key required.

Usage:
    from core.ai.stt import WhisperClient

    text = WhisperClient.transcribe(audio_bytes, filename="clip.webm")
"""

import io
import tempfile
import os
from typing import Optional

from decouple import config

_MODEL_SIZE = config("WHISPER_MODEL", default="tiny")
_LANGUAGE   = config("WHISPER_LANGUAGE", default="vi")

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
        print(f"[Whisper] model '{_MODEL_SIZE}' loaded")
    return _model


class WhisperClient:

    @classmethod
    def transcribe(
        cls,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> str:
        """Transcribe raw audio bytes → text string."""
        lang = language or _LANGUAGE
        suffix = os.path.splitext(filename)[-1] or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            model = _get_model()
            segments, _ = model.transcribe(tmp_path, language=lang, beam_size=1)
            text = " ".join(seg.text.strip() for seg in segments).strip()
            print(f"[Whisper] transcript ({len(text)} chars): {text[:100]!r}")
            return text
        finally:
            os.unlink(tmp_path)

    @classmethod
    def transcribe_file(cls, file_obj, language: Optional[str] = None) -> str:
        """Convenience wrapper for Django InMemoryUploadedFile / TemporaryUploadedFile."""
        filename = getattr(file_obj, "name", "audio.webm")
        audio_bytes = file_obj.read()
        return cls.transcribe(audio_bytes, filename=filename, language=language)
