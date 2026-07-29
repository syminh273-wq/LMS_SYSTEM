from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import SpaceScopeMixin
from features.ai.services.ai_conversation_session_service import AIConversationSessionService
from features.course.classroom.services import ClassroomAIService

_ai_session_service = AIConversationSessionService()

_CLASSROOM_PROMPT = (
    "Bạn là AI Trợ giảng, hỗ trợ học sinh và giáo viên hiểu sâu nội dung bài học.\n\n"
    "QUY TẮC BẮT BUỘC:\n"
    "- Với BẤT KỲ câu hỏi nào về nội dung, tài liệu, bài học, nhân vật, sự kiện, khái niệm: "
    "BẮT BUỘC phải gọi tool search_documents TRƯỚC, sau đó mới trả lời dựa trên kết quả.\n"
    "- KHÔNG được tự trả lời từ kiến thức của mình. KHÔNG được nói 'không tìm thấy' mà chưa gọi tool.\n"
    "- Chỉ bỏ qua search_documents với lời chào xã giao (Xin chào, Hi, Hello,...).\n\n"
    "Khi trả lời dựa trên kết quả tool:\n"
    "1. Trả lời đầy đủ và có chiều sâu — giải thích để người học thực sự hiểu.\n"
    "2. Dẫn chứng cụ thể từ tài liệu — dùng câu như 'Theo tài liệu...', 'Bài học nêu rõ rằng...'.\n"
    "3. Văn phong tự nhiên, thân thiện như người thầy đang giảng.\n"
    "4. Cấu trúc rõ ràng — chia đoạn hoặc liệt kê có thứ tự nếu có nhiều ý.\n"
    "5. Nếu kết quả search_documents trống hoặc không liên quan: CHỈ nói 'Tài liệu lớp học không có thông tin về vấn đề này.'\n\n"
    "CHỈ trả lời bằng tiếng Việt."
)


class SpaceClassroomAIViewSet(SpaceScopeMixin, ViewSet):
    """AI Q&A endpoints for the teacher (Space) classroom view. Split out of SpaceClassroomViewSet."""

    @action(detail=True, methods=['post'], url_path='ask')
    def ask(self, request, uid=None):
        """
        Ask the classroom AI a question and get a synchronous answer.
        @param question: the question text
        @return: answer, tool_calls, session_id
        """
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)

        ai_service = ClassroomAIService()
        session_id = ai_service.get_session_id(
            request.data.get('session_id'), request.user.uid, uid
        )

        filter_meta = {'classroom_id': str(uid)}
        section = request.data.get('section')
        if section:
            filter_meta['section'] = section

        result = ai_service.ask(
            question=question,
            session_id=session_id,
            user_id=request.user.uid,
            classroom_id=uid,
            filter_meta=filter_meta,
            system_prompt=_CLASSROOM_PROMPT
        )

        return Response({
            'answer':     result['answer'],
            'tool_calls': result['tool_calls'],
            'session_id': session_id,
        })

    @action(detail=True, methods=['post'], url_path='ask-stream')
    def ask_stream(self, request, uid=None):
        """
        Ask the classroom AI a question and stream the answer via SSE.
        @param question: the question text
        @return: text/event-stream response
        """
        ai_service = ClassroomAIService()

        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)

        session_id = ai_service.get_session_id(
            request.data.get('session_id'), request.user.uid, uid
        )

        mode = (request.data.get('mode') or 'doc').strip()
        section = request.data.get('section')
        document_id = request.data.get('document_id')

        resp = StreamingHttpResponse(
            ai_service.ask_stream(
                question=question,
                session_id=session_id,
                user_id=request.user.uid,
                classroom_id=uid,
                mode=mode,
                document_id=document_id,
                section=section
            ),
            content_type='text/event-stream; charset=utf-8'
        )
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp

    @action(detail=True, methods=['get'], url_path='active-session')
    def active_session(self, request, uid=None):
        """
        Continue the most recent AI session or create a new one.
        @return: session_id, messages
        """
        session_id = _ai_session_service.ensure_session(None, request.user.uid, str(uid))
        messages = _ai_session_service.get_display_messages(session_id)
        return Response({
            'session_id': session_id,
            'messages': messages
        })

    @action(detail=True, methods=['post'], url_path='ai-session')
    def ai_session(self, request, uid=None):
        """
        Create a new AI session, or clear and replace an existing one.
        @param session_id: existing session to clear (optional)
        @return: session_id
        """
        old_sid = (request.data.get('session_id') or '').strip()
        if old_sid and _ai_session_service.session_exists(old_sid):
            new_sid = _ai_session_service.clear_session(
                old_sid, user_id=request.user.uid, classroom_id=str(uid)
            )
        else:
            new_sid = _ai_session_service.create_session(
                user_id=request.user.uid, classroom_id=str(uid)
            )
        return Response({'session_id': new_sid})

    @action(detail=True, methods=['get'], url_path='ai-sessions')
    def ai_sessions(self, request, uid=None):
        """
        List all AI sessions for this teacher in this classroom.
        @return: list of sessions
        """
        sessions = _ai_session_service.list_sessions(
            user_id=request.user.uid, classroom_id=str(uid)
        )
        return Response(sessions)

    @action(detail=True, methods=['get'], url_path='ai-session/history')
    def ai_session_history(self, request, uid=None):
        """
        Get the message history for an AI session.
        @param session_id: the session to fetch history for
        @return: session_id, messages
        """
        session_id = (request.query_params.get('session_id') or '').strip()
        if not session_id or not _ai_session_service.session_exists(session_id):
            return Response({'error': 'Session không hợp lệ.'}, status=status.HTTP_404_NOT_FOUND)
        messages = _ai_session_service.get_display_messages(session_id)
        return Response({'session_id': session_id, 'messages': messages})
