import uuid

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.ai.langchain.agent import LMSAgent
from core.ai.langchain.tools import build_langchain_tools
from core.ai.tools.tool_executor import LMSToolExecutor
from core.views.mixins import ConsumerScopeMixin
from features.ai.services.ai_conversation_session_service import AIConversationSessionService
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
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


class ConsumerClassroomAIViewSet(ConsumerScopeMixin, ViewSet):
    """AI Q&A endpoints for the student (Consumer) classroom view. Split out of ConsumerClassroomViewSet."""

    def _check_member(self, classroom_uid, user_uid):
        member = ClassroomMemberRepository().get_member(uuid.UUID(str(classroom_uid)), user_uid)
        if not member or member.is_deleted or member.status != 'approved':
            return False
        return True

    @action(detail=True, methods=['post'], url_path='ask')
    def ask(self, request, pk=None):
        """
        Ask the classroom AI a question and get a synchronous answer.
        @param question: the question text
        @return: answer, tool_calls, session_id
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(request.user.uid)
        classroom_id = str(pk)
        session_id = (request.data.get('session_id') or '').strip()
        session_id = _ai_session_service.ensure_session(session_id, user_id, classroom_id)

        section = request.data.get('section')
        filter_meta = {'classroom_id': classroom_id}
        if section:
            filter_meta['section'] = section

        executor = LMSToolExecutor(teacher_id=user_id, filter_meta=filter_meta)
        tools = build_langchain_tools(executor, has_classroom=False)
        result = LMSAgent(tools, system_prompt=_CLASSROOM_PROMPT).ask(question, session_id)

        return Response({
            'answer':     result['answer'],
            'tool_calls': result['tool_calls'],
            'session_id': session_id,
        })

    @action(detail=True, methods=['post'], url_path='ask-stream')
    def ask_stream(self, request, pk=None):
        """
        Ask the classroom AI a question and stream the answer via SSE.
        @param question: the question text
        @return: text/event-stream response
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        ai_service = ClassroomAIService()

        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(request.user.uid)
        classroom_id = str(pk)
        session_id = ai_service.get_session_id(
            request.data.get('session_id'), user_id, classroom_id
        )

        mode = (request.data.get('mode') or 'doc').strip()
        section = request.data.get('section')
        document_id = request.data.get('document_id')

        resp = StreamingHttpResponse(
            ai_service.ask_stream(
                question=question,
                session_id=session_id,
                user_id=request.user.uid,
                classroom_id=pk,
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
    def active_session(self, request, pk=None):
        """
        Continue the student's most recent AI session or create a new one.
        @return: session_id, messages
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        session_id = _ai_session_service.ensure_session(None, request.user.uid, str(pk))
        messages = _ai_session_service.get_display_messages(session_id)

        return Response({
            'session_id': session_id,
            'messages': messages
        })

    @action(detail=True, methods=['post'], url_path='ai-session')
    def ai_session(self, request, pk=None):
        """
        Create a new AI session, or clear and replace an existing one.
        @param session_id: existing session to clear (optional)
        @return: session_id
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        old_sid = (request.data.get('session_id') or '').strip()
        if old_sid and _ai_session_service.session_exists(old_sid):
            new_sid = _ai_session_service.clear_session(
                old_sid, user_id=request.user.uid, classroom_id=str(pk)
            )
        else:
            new_sid = _ai_session_service.create_session(
                user_id=request.user.uid, classroom_id=str(pk)
            )
        return Response({'session_id': new_sid})

    @action(detail=True, methods=['get'], url_path='ai-sessions')
    def ai_sessions(self, request, pk=None):
        """
        List all AI sessions for the current student in this classroom.
        @return: list of sessions
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        sessions = _ai_session_service.list_sessions(
            user_id=request.user.uid, classroom_id=str(pk)
        )
        return Response(sessions)

    @action(detail=True, methods=['get'], url_path='ai-session/history')
    def ai_session_history(self, request, pk=None):
        """
        Get the message history for an AI session.
        @param session_id: the session to fetch history for
        @return: session_id, messages
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        session_id = (request.query_params.get('session_id') or '').strip()
        if not session_id or not _ai_session_service.session_exists(session_id):
            return Response({'error': 'Session không hợp lệ.'}, status=status.HTTP_404_NOT_FOUND)
        messages = _ai_session_service.get_display_messages(session_id)
        return Response({'session_id': session_id, 'messages': messages})
