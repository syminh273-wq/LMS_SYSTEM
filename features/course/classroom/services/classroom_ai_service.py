import json
import base64
from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.ai.llm.services.ai_client import AIClient
from core.ai.stt import WhisperClient
from core.ai.tts import TTSClient
from core.ai.tools.tool_executor import LMSToolExecutor
from core.ai.langchain.tools import build_langchain_tools
from core.ai.langchain.agent import LMSAgent
from features.ai.services.ai_conversation_session_service import AIConversationSessionService

class ClassroomAIService:
    def __init__(self):
        self.session_service = AIConversationSessionService()

    def transcribe_audio(self, audio_file):
        """Transcribe audio file to text using Whisper."""
        if not audio_file:
            return None
        return WhisperClient.transcribe_file(audio_file)

    def synthesize_text(self, text):
        """Synthesize text to MP3 bytes using TTS."""
        return TTSClient.synthesize(text)

    def get_session_id(self, session_id, user_id, classroom_id):
        """Ensure a valid session ID exists."""
        return self.session_service.ensure_session(session_id, str(user_id), str(classroom_id))

    def ask(self, question, session_id, user_id, classroom_id, filter_meta, system_prompt):
        """Synchronous AI response."""
        executor = LMSToolExecutor(teacher_id=str(user_id), filter_meta=filter_meta)
        tools = build_langchain_tools(executor, has_classroom=True)
        return LMSAgent(tools, system_prompt=system_prompt).ask(question, session_id)

    def ask_stream(self, question, session_id, user_id, classroom_id, mode='doc', section=None):
        """Generator for AI streaming response."""
        filter_meta = {'classroom_id': str(classroom_id)}
        if section:
            filter_meta['section'] = section

        yield f'data: {json.dumps({"type": "session_id", "session_id": session_id, "transcript": question}, ensure_ascii=False)}\n\n'

        full_response = []
        try:
            if mode == 'doc':
                for chunk in self._handle_doc_mode(question, filter_meta):
                    if isinstance(chunk, str):
                        full_response.append(chunk)
                        yield f'data: {json.dumps({"type": "chunk", "text": chunk}, ensure_ascii=False)}\n\n'
                    elif isinstance(chunk, tuple) and chunk[0] == "__ERROR__":
                        yield f'data: {json.dumps({"type": "error", "message": str(chunk[1])}, ensure_ascii=False)}\n\n'

            elif mode == 'manage':
                for chunk in self._handle_manage_mode(question, session_id, user_id, filter_meta):
                    if isinstance(chunk, tuple):
                        signal, data = chunk
                        if signal == "__TOOL_CALLS__":
                            payload = json.dumps({'type': 'tool_calls', 'data': data}, ensure_ascii=False)
                        elif signal == "__ERROR__":
                            payload = json.dumps({'type': 'error', 'message': str(data)}, ensure_ascii=False)
                        else:
                            continue
                    else:
                        full_response.append(chunk)
                        payload = json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)
                    yield f'data: {payload}\n\n'

            else:  # 'free'
                for chunk in self._handle_free_mode(question):
                    if isinstance(chunk, str):
                        full_response.append(chunk)
                        yield f'data: {json.dumps({"type": "chunk", "text": chunk}, ensure_ascii=False)}\n\n'
                    elif isinstance(chunk, tuple) and chunk[0] == "__ERROR__":
                        yield f'data: {json.dumps({"type": "error", "message": str(chunk[1])}, ensure_ascii=False)}\n\n'

            # TTS Support
            full_text = "".join(full_response).strip()
            if full_text:
                audio_chunk = self._generate_tts_chunk(full_text)
                if audio_chunk:
                    yield audio_chunk

        except Exception as exc:
            yield f'data: {json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)}\n\n'
        finally:
            yield 'data: [DONE]\n\n'

    def _handle_doc_mode(self, question, filter_meta):
        hits = RAGPipeline().search(question, top_k=3, filter_meta=filter_meta)
        context = "\n\n---\n\n".join(h["document"] for h in hits) if hits else ""
        
        if context:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Bạn là AI Trợ giảng. Trả lời câu hỏi DỰA HOÀN TOÀN vào phần TÀI LIỆU được cung cấp. "
                        "Nếu tài liệu không có thông tin: chỉ nói 'Tài liệu lớp học không có thông tin về vấn đề này.' "
                        "CHỈ trả lời bằng tiếng Việt."
                    ),
                },
                {
                    "role": "user",
                    "content": f"TÀI LIỆU:\n{context}\n\nCÂU HỎI: {question}",
                },
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": "Bạn là AI Trợ giảng. CHỈ trả lời bằng tiếng Việt.",
                },
                {
                    "role": "user",
                    "content": "Lớp học chưa có tài liệu nào. Hãy thông báo và gợi ý giáo viên tải tài liệu lên.",
                },
            ]
        return AIClient.chat_stream(messages, timeout=300)

    def _handle_manage_mode(self, question, session_id, user_id, filter_meta):
        executor = LMSToolExecutor(teacher_id=str(user_id), filter_meta=filter_meta)
        tools = build_langchain_tools(executor, has_classroom=True, include_search=False)
        system_prompt = (
            "Bạn là AI quản lý lớp học. Sử dụng các công cụ để truy vấn dữ liệu lớp học "
            "(danh sách học sinh, thống kê bài thi, thông tin lớp...).\n"
            "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
        )
        agent = LMSAgent(tools, system_prompt=system_prompt)
        return agent.ask_stream(question, session_id)

    def _handle_free_mode(self, question):
        messages = [
            {"role": "system", "content": "Bạn là trợ lý AI thông minh. Trả lời bằng tiếng Việt, thân thiện và hữu ích."},
            {"role": "user",   "content": question},
        ]
        return AIClient.chat_stream(messages, timeout=300)

    def _generate_tts_chunk(self, text):
        try:
            audio_bytes = TTSClient.synthesize(text)
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            return f'data: {json.dumps({"type": "audio", "audio": audio_b64}, ensure_ascii=False)}\n\n'
        except Exception as e:
            print(f"[TTS] Error: {e}")
            return None
