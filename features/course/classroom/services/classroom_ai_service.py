"""
ClassroomAIService — orchestration layer cho classroom AI.

Kiến trúc (chuẩn RAG)
──────────────────────
  ViewSet (HTTP / WS)
        ↓
  ClassroomAIService   ← chỉ làm orchestration: permission, session, SSE
        ↓
  RAGPipeline          ← retrieve / build_context / generate_stream
        ↓
  LanceVectorService + Embedding + LLM

Mode handling
─────────────
  doc     — RAG retrieval + LLM streaming (câu hỏi về tài liệu lớp)
  manage  — LangChain tool-calling agent (quản lý lớp: học sinh, bài thi…)
  free    — LLM thuần, không retrieval (chat tự do)
"""

import base64
import json
from typing import Generator

from core.ai.langchain.agent import LMSAgent
from core.ai.langchain.tools import build_langchain_tools
from core.ai.llm.services.ai_client import AIClient
from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.ai.stt import WhisperClient
from core.ai.tools.tool_executor import LMSToolExecutor
from core.ai.tts import TTSClient
from features.account.user_setting.services.user_setting_service import UserSettingService
from features.ai.services.ai_conversation_session_service import AIConversationSessionService

# Module-level singleton — tránh re-instantiate RAGPipeline (giữ _store_cache)
_pipeline = RAGPipeline()

_DOC_MODE_SYSTEM_PROMPT = (
    "Bạn là AI Trợ giảng. Nhiệm vụ: tổng hợp và trả lời câu hỏi của người dùng DỰA TRÊN "
    "phần TÀI LIỆU được cung cấp bên dưới.\n\n"
    "Quy tắc:\n"
    "1. ĐỌC kỹ toàn bộ tài liệu trước khi trả lời.\n"
    "2. Nếu tài liệu có thông tin liên quan (dù chỉ một phần) → tổng hợp và trả lời "
    "đầy đủ, trích dẫn từ tài liệu.\n"
    "3. CHỈ trả lời 'Tài liệu lớp học không có thông tin về vấn đề này' khi tài liệu "
    "thật sự KHÔNG chứa bất kỳ thông tin nào liên quan đến câu hỏi.\n"
    "4. Trả lời bằng tiếng Việt, văn phong thân thiện, dễ hiểu.\n\n"
    "TÀI LIỆU THAM KHẢO:\n{context}"
)

_MANAGE_MODE_SYSTEM_PROMPT = (
    "Bạn là AI quản lý lớp học. Sử dụng các công cụ để truy vấn dữ liệu lớp học "
    "(danh sách học sinh, thống kê bài thi, thông tin lớp...).\n"
    "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
)

_FREE_MODE_SYSTEM_PROMPT = (
    "Bạn là trợ lý AI thông minh. Trả lời bằng tiếng Việt, thân thiện và hữu ích."
)


class ClassroomAIService:
    def __init__(self):
        self.session_service = AIConversationSessionService()
        self.setting_service = UserSettingService()

    # ── STT / TTS helpers ─────────────────────────────────────────────────────

    def transcribe_audio(self, audio_file):
        if not audio_file:
            return None
        return WhisperClient.transcribe_file(audio_file)

    def synthesize_text(self, text, user_id=None):
        voice = None
        if user_id:
            voice = self.setting_service.get_setting(user_id, "voice_name")
        return TTSClient.synthesize(text, voice=voice)

    # ── Session ───────────────────────────────────────────────────────────────

    def get_session_id(self, session_id, user_id, classroom_id):
        return self.session_service.ensure_session(session_id, str(user_id), str(classroom_id))

    # ── Public API ────────────────────────────────────────────────────────────

    def ask(self, question, session_id, user_id, classroom_id, filter_meta, system_prompt):
        """Synchronous AI response (manage mode với tool-calling)."""
        executor = LMSToolExecutor(teacher_id=str(user_id), filter_meta=filter_meta)
        tools = build_langchain_tools(executor, has_classroom=True)
        return LMSAgent(tools, system_prompt=system_prompt).ask(question, session_id)

    def ask_stream(
        self,
        question: str,
        session_id: str,
        user_id,
        classroom_id,
        mode: str = "doc",
        document_id: str = None,
        section: str = None,
    ) -> Generator[str, None, None]:
        """
        SSE-friendly generator.

        Flow:
          1. Yield 'session_id' event (kèm transcript) để client biết session
          2. Theo mode:
              doc    → RAGPipeline.ask_stream (retrieve + LLM stream)
              manage → LMSAgent.ask_stream (tool-calling agent)
              free   → AIClient.chat_stream (raw LLM)
          3. Nếu user bật voice → yield 'audio' event với MP3 base64
          4. Always yield 'data: [DONE]\\n\\n' cuối cùng
        """
        is_voice_enabled = self.setting_service.get_setting(user_id, "is_voice_enabled", "false").lower() == "true"
        voice_name = self.setting_service.get_setting(user_id, "voice_name")

        yield self._sse({"type": "session_id", "session_id": session_id, "transcript": question})

        full_response: list = []
        sources_payload: list = []
        try:
            if mode == "doc":
                for item in self._handle_doc_mode(
                    question=question,
                    classroom_id=classroom_id,
                    document_id=document_id,
                    section=section,
                ):
                    if isinstance(item, str):
                        full_response.append(item)
                        yield self._sse({"type": "chunk", "text": item})
                    elif isinstance(item, tuple):
                        signal, data = item
                        if signal == "__SOURCES__":
                            sources_payload = data or []
                        elif signal == "__NO_DOC__":
                            full_response.append(data)
                            yield self._sse({"type": "chunk", "text": data})
                        elif signal == "__ERROR__":
                            yield self._sse({"type": "error", "message": str(data)})

            elif mode == "manage":
                for item in self._handle_manage_mode(question, session_id, user_id, classroom_id):
                    if isinstance(item, tuple):
                        signal, data = item
                        if signal == "__TOOL_CALLS__":
                            yield self._sse({"type": "tool_calls", "data": data})
                        elif signal == "__ERROR__":
                            yield self._sse({"type": "error", "message": str(data)})
                        else:
                            continue
                    else:
                        full_response.append(item)
                        yield self._sse({"type": "chunk", "text": item})

            else:  # 'free'
                for item in self._handle_free_mode(question):
                    if isinstance(item, str):
                        full_response.append(item)
                        yield self._sse({"type": "chunk", "text": item})
                    elif isinstance(item, tuple) and item[0] == "__ERROR__":
                        yield self._sse({"type": "error", "message": str(item[1])})

            # Yield sources cuối cùng (doc mode)
            if sources_payload:
                yield self._sse({"type": "sources", "data": sources_payload})

            # TTS nếu user bật voice
            if is_voice_enabled and mode != "manage":
                full_text = "".join(full_response).strip()
                if full_text:
                    audio_chunk = self._generate_tts_chunk(full_text, voice=voice_name)
                    if audio_chunk:
                        yield audio_chunk

            # Lưu lịch sử hội thoại
            full_answer = "".join(full_response).strip()
            if full_answer and mode in ("doc", "free"):
                try:
                    self.session_service.save_turn(session_id, question, full_answer)
                except Exception as exc:
                    print(f"[ClassroomAIService] Failed to save turn: {exc}")

        except Exception as exc:
            yield self._sse({"type": "error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    # ── Mode handlers ─────────────────────────────────────────────────────────

    def _handle_doc_mode(
        self,
        question: str,
        classroom_id,
        document_id: str = None,
        section: str = None,
    ):
        """
        Mode 'doc': RAG retrieval + LLM streaming.

        Truyền rõ ràng classroom_id + document_id + section (theo spec),
        không truyền filter_meta dict chung chung.
        """
        return _pipeline.ask_stream(
            question=question,
            classroom_id=str(classroom_id),
            document_id=str(document_id) if document_id else None,
            section=section,
            system_prompt=_DOC_MODE_SYSTEM_PROMPT,
        )

    def _handle_manage_mode(self, question, session_id, user_id, classroom_id):
        filter_meta = {"classroom_id": str(classroom_id)}
        executor = LMSToolExecutor(teacher_id=str(user_id), filter_meta=filter_meta)
        tools = build_langchain_tools(executor, has_classroom=True, include_search=False)
        agent = LMSAgent(tools, system_prompt=_MANAGE_MODE_SYSTEM_PROMPT)
        return agent.ask_stream(question, session_id)

    def _handle_free_mode(self, question):
        messages = [
            {"role": "system", "content": _FREE_MODE_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        return AIClient.chat_stream(messages, timeout=300)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _generate_tts_chunk(self, text, voice=None):
        try:
            audio_bytes = TTSClient.synthesize(text, voice=voice)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return self._sse({"type": "audio", "audio": audio_b64})
        except Exception as exc:
            print(f"[TTS] Error: {exc}")
            return None
