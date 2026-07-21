import json
import uuid

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.ai.llm.services.ai_client import AIClient
from core.ai.tools.tool_executor import LMSToolExecutor
from core.ai.langchain.tools import build_langchain_tools
from core.ai.langchain.agent import LMSAgent
from core.serializers.classroom import ClassroomResponseSerializer
from core.views.api.pagination import StandardResultsSetPagination
from core.views.mixins import UserScopeMixin
from features.ai.services.ai_conversation_session_service import AIConversationSessionService
from features.chat.serializers.conversation_serializer import ConversationSerializer
from features.chat.services.conversation_service import ConversationService
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.classroom.services import Service, ClassroomAIService
from features.course.classroom.services.classroom_member_service import ClassroomMemberService

_ai_session_service = AIConversationSessionService()


class ConsumerClassroomViewSet(UserScopeMixin, ViewSet):
    """Classroom endpoints for students (Consumer accounts)."""

    pagination_class = StandardResultsSetPagination

    def list(self, request):
        """GET /api/v1/consumer/course/classrooms/ — chỉ trả về lớp đã tham gia."""
        uids = ClassroomMemberService().get_joined_classroom_uids(request.user.uid)
        service = Service()
        classrooms = []
        for uid in uids:
            try:
                classroom = service.find(str(uid))
                if getattr(classroom, 'status', 'active') == 'private':
                    continue
                classrooms.append(classroom)
            except Exception:
                continue
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(classrooms, request)
        if page is not None:
            return paginator.get_paginated_response(ClassroomResponseSerializer(page, many=True).data)
        return Response(ClassroomResponseSerializer(classrooms, many=True).data)

    def retrieve(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/"""
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        import uuid as _uuid
        try:
            classroom_uid = _uuid.UUID(str(pk))
        except ValueError:
            return Response({'error': 'ID lớp không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        instance = Service().find(pk)
        if getattr(instance, 'status', 'active') == 'private':
            return Response({'error': 'Lớp học này không khả dụng.'}, status=status.HTTP_403_FORBIDDEN)
        from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService
        if ClassroomBlacklistService().is_blocked(instance.uid, instance.teacher_id, request.user.uid):
            return Response({'error': 'Bạn đã bị chặn khỏi lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        member = ClassroomMemberRepository().get_member(classroom_uid, request.user.uid)
        has_paid = bool(member and not member.is_deleted and getattr(member, 'has_paid', False) and member.status == 'approved')
        is_paid_classroom = getattr(instance, 'pricing_type', 'free') == 'paid'

        if is_paid_classroom and not has_paid:
            data = ClassroomResponseSerializer(instance).data
            data['has_access'] = False
            data['has_paid'] = False
            data['requires_payment'] = True
            data['membership_status'] = getattr(member, 'status', None) if member else None
            return Response(data)

        if not member or member.is_deleted:
            return Response({'error': 'Bạn chưa đăng ký tham gia lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        if member.status == 'pending':
            return Response(
                {'error': 'Yêu cầu của bạn đang chờ giáo viên phê duyệt.', 'membership_status': 'pending'},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = ClassroomResponseSerializer(instance).data
        data['has_access'] = True
        data['has_paid'] = has_paid
        data['requires_payment'] = False
        return Response(data)

    @action(detail=False, methods=['post'], url_path='join')
    def join_by_code(self, request):
        """POST /api/v1/consumer/course/classrooms/join/  body: {"code": "ABCDEF"}"""
        code = (request.data.get('code') or '').strip().upper()
        if not code:
            return Response({'error': 'Mã lớp không được để trống.'}, status=status.HTTP_400_BAD_REQUEST)

        from features.course.classroom.repositories import Repository
        from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService
        classroom = Repository().filter(pid=code).first()
        if not classroom or getattr(classroom, 'is_deleted', False) or classroom.status not in ('active',):
            return Response({'error': 'Mã lớp không hợp lệ hoặc lớp không còn hoạt động.'}, status=status.HTTP_404_NOT_FOUND)

        if ClassroomBlacklistService().is_blocked(classroom.uid, classroom.teacher_id, request.user.uid):
            return Response({'error': 'Bạn đã bị chặn khỏi lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        if getattr(classroom, 'pricing_type', 'free') == 'paid':
            try:
                from features.payment.services import PaymentService
                result = PaymentService().initiate(
                    consumer_id=str(request.user.uid),
                    amount=int(classroom.price_vnd or 0),
                    order_info=f'Lớp học: {classroom.name}',
                    resource_type='classroom',
                    resource_id=str(classroom.uid),
                )
            except Exception as exc:
                return Response({'error': f'Khởi tạo thanh toán thất bại: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'requires_payment': True,
                'membership_status': 'pending',
                'classroom_uid': str(classroom.uid),
                'amount': int(classroom.price_vnd or 0),
                **result,
            })

        member = ClassroomMemberService().join(classroom_uid=classroom.uid, user=request.user, role='student')
        member_status = getattr(member, 'status', 'approved')
        return Response(
            {
                'requires_payment': False,
                'membership_status': member_status,
                'message': 'Tham gia lớp thành công' if member_status == 'approved' else 'Đã gửi lời mời tham gia lớp này',
                'classroom_uid': str(classroom.uid),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='checkout')
    def checkout(self, request, pk=None):
        """POST /api/v1/consumer/course/classrooms/{uid}/checkout/ — initiate MoMo for a paid classroom."""
        from features.course.classroom.repositories import Repository
        try:
            classroom = Repository().find(str(pk))
        except Exception:
            return Response({'error': 'Lớp học không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        if getattr(classroom, 'pricing_type', 'free') != 'paid':
            return Response({'error': 'Lớp học này miễn phí, không cần thanh toán.'}, status=status.HTTP_400_BAD_REQUEST)
        if int(classroom.price_vnd or 0) < 1000:
            return Response({'error': 'Giá lớp học không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        from features.course.classroom.services.classroom_member_service import ClassroomMemberService
        from features.payment.services import PaymentService
        ClassroomMemberService().join(classroom_uid=classroom.uid, user=request.user, role='student')

        try:
            result = PaymentService().initiate(
                consumer_id=str(request.user.uid),
                amount=int(classroom.price_vnd),
                order_info=f'Lớp học: {classroom.name}',
                resource_type='classroom',
                resource_id=str(classroom.uid),
            )
        except Exception as exc:
            return Response({'error': f'Khởi tạo thanh toán thất bại: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'classroom_uid': str(classroom.uid),
            'amount': int(classroom.price_vnd),
            **result,
        })

    @action(detail=True, methods=['get'], url_path='access')
    def access(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/access/ — poll endpoint for checkout flow."""
        return Response(Service().get_access_for_consumer(str(pk), consumer_id=str(request.user.uid)))

    @action(detail=True, methods=['get'], url_path='preview-folder')
    def preview_folder(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/preview-folder/ — always accessible."""
        from features.resource.serializers.resource_folder_serializer import ResourceFolderResponseSerializer
        from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer

        folder = ClassroomDocService().get_preview_folder(str(pk))
        if not folder:
            return Response({'folder': None, 'docs': []})
        docs = ClassroomDocService().list_folder(classroom_uid=str(pk), folder_id=str(folder.uid))
        return Response({
            'folder': ResourceFolderResponseSerializer(folder).data,
            'docs': ResourceResponseSerializer(docs, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def conversation(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/conversation/"""
        conv = ConversationService().get_or_create_channel(
            classroom_uid=uuid.UUID(str(pk)),
            created_by_id=request.user.uid,
        )
        return Response(ConversationSerializer(conv).data)

    # ── AI Bot ────────────────────────────────────────────────────────────────

    _CLASSROOM_PROMPT = (
        "Bạn là AI Trợ giảng, hỗ trợ học sinh hiểu sâu nội dung bài học.\n\n"
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

    def _check_member(self, classroom_uid, user_uid):
        member = ClassroomMemberRepository().get_member(uuid.UUID(str(classroom_uid)), user_uid)
        if not member or member.is_deleted or member.status != 'approved':
            return False
        return True

    @action(detail=True, methods=['post'], url_path='ask')
    def ask(self, request, pk=None):
        """POST /api/v1/consumer/course/classrooms/{uid}/ask/"""
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
        result = LMSAgent(tools, system_prompt=self._CLASSROOM_PROMPT).ask(question, session_id)

        return Response({
            'answer':     result['answer'],
            'tool_calls': result['tool_calls'],
            'session_id': session_id,
        })

    @action(detail=True, methods=['post'], url_path='ask-stream')
    def ask_stream(self, request, pk=None):
        """POST /api/v1/consumer/course/classrooms/{uid}/ask-stream/ — SSE streaming RAG Q&A."""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        
        ai_service = ClassroomAIService()
        
        # Handle Audio STT
        audio_file = request.FILES.get('audio')
        if audio_file:
            try:
                question = ai_service.transcribe_audio(audio_file)
            except Exception as exc:
                return Response({'error': f'Không thể nhận dạng giọng nói: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        else:
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

        resp = StreamingHttpResponse(
            ai_service.ask_stream(
                question=question,
                session_id=session_id,
                user_id=request.user.uid,
                classroom_id=pk,
                mode=mode,
                section=section
            ),
            content_type='text/event-stream; charset=utf-8'
        )
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp

    @action(detail=True, methods=['get'], url_path='docs')
    def docs(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/docs/"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        from features.course.classroom.services.classroom_doc_service import ClassroomDocService
        from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer

        section = request.query_params.get('section')
        folder_id = request.query_params.get('folder_id') or None
        doc_service = ClassroomDocService()
        if folder_id or 'folder_id' in request.query_params:
            docs = doc_service.list_folder(classroom_uid=str(pk), folder_id=folder_id)
        else:
            docs = doc_service.list_docs(classroom_uid=str(pk), section=section)
        return Response(ResourceResponseSerializer(docs, many=True).data)

    @action(detail=True, methods=['get'], url_path='docs/tree')
    def docs_tree(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/docs/tree/ — read-only mirror.

        Paid + non-member → only preview folder + preview docs.
        Paid + member   → full tree.
        Free            → full tree (no member check).
        """
        from features.course.classroom.services.classroom_doc_service import ClassroomDocService
        from features.resource.serializers.resource_folder_serializer import ResourceFolderResponseSerializer
        from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer

        from features.course.classroom.repositories import Repository
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        try:
            classroom = Repository().find(str(pk))
        except Exception:
            return Response({'error': 'Lớp học không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        consumer_id = str(request.user.uid)
        is_paid_classroom = getattr(classroom, 'pricing_type', 'free') == 'paid'
        has_access = True
        if is_paid_classroom:
            member = ClassroomMemberRepository().get_paid_member(pk, consumer_id)
            has_access = member is not None

        if not has_access:
            tree = ClassroomDocService().list_tree(classroom_uid=str(pk), consumer_id=consumer_id)
            return Response({
                'folders': ResourceFolderResponseSerializer(tree['folders'], many=True).data,
                'docs_root': ResourceResponseSerializer(tree['docs_root'], many=True).data,
                'preview_only': True,
                'requires_payment': True,
            })

        if not self._check_member(pk, consumer_id):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        tree = ClassroomDocService().list_tree(classroom_uid=str(pk), consumer_id=consumer_id)
        return Response({
            'folders': ResourceFolderResponseSerializer(tree['folders'], many=True).data,
            'docs_root': ResourceResponseSerializer(tree['docs_root'], many=True).data,
            'preview_only': tree.get('preview_only', False),
            'requires_payment': False,
        })

    # ── Doc reading progress + notes ─────────────────────────────────────────

    @action(detail=True, methods=['get', 'post'], url_path=r'docs/(?P<resource_uid>[^/.]+)/progress')
    def doc_progress(self, request, pk=None, resource_uid=None):
        """GET/POST /api/v1/consumer/course/classrooms/{uid}/docs/{resource_uid}/progress/"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        from features.course.classroom.services.doc_progress_helpers import (
            get_student_progress,
            mark_progress,
        )

        if request.method == 'GET':
            data = get_student_progress(str(pk), request.user.uid, resource_uid)
            return Response(data)

        return Response(mark_progress(str(pk), request.user.uid, resource_uid, request.data or {}))

    @action(detail=True, methods=['post'], url_path=r'docs/(?P<resource_uid>[^/.]+)/complete')
    def doc_complete(self, request, pk=None, resource_uid=None):
        """POST /api/v1/consumer/course/classrooms/{uid}/docs/{resource_uid}/complete/"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        from features.course.classroom.services.doc_progress_helpers import mark_completed
        is_done = bool((request.data or {}).get('is_completed', True))
        return Response(mark_completed(str(pk), request.user.uid, resource_uid, is_done))

    @action(detail=True, methods=['get', 'post'], url_path=r'docs/(?P<resource_uid>[^/.]+)/notes')
    def doc_notes(self, request, pk=None, resource_uid=None):
        """GET/POST /api/v1/consumer/course/classrooms/{uid}/docs/{resource_uid}/notes/"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        from features.course.classroom.services.doc_progress_helpers import (
            list_notes_for_resource,
            create_note,
        )

        if request.method == 'GET':
            only_mine = bool((request.query_params.get('only_mine') or '').lower() in ('1', 'true', 'yes'))
            sid = request.user.uid if only_mine else None
            return Response(list_notes_for_resource(resource_uid, student_id=sid))

        try:
            note = create_note(str(pk), request.user.uid, resource_uid, request.data or {})
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(note, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'docs/(?P<resource_uid>[^/.]+)/notes/(?P<note_uid>[^/.]+)')
    def doc_note_detail(self, request, pk=None, resource_uid=None, note_uid=None):
        """PATCH/DELETE /api/v1/consumer/course/classrooms/{uid}/docs/{rid}/notes/{nid}/"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        from features.resource.services import DocNoteService
        from features.course.classroom.services.doc_progress_helpers import update_note, delete_note

        try:
            note = DocNoteService().find(note_uid)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if str(note.student_id) != str(request.user.uid):
            return Response({'error': 'Bạn không có quyền sửa note này.'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'DELETE':
            delete_note(note)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(update_note(note, request.data or {}))

    @action(detail=True, methods=['get'], url_path='active-session')
    def active_session(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/active-session/
        Tự động tiếp tục session gần nhất hoặc tạo mới, trả về cả ID và lịch sử tin nhắn.
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
        """POST /api/v1/consumer/course/classrooms/{uid}/ai-session/

        No body           → create new session
        { session_id }    → clear old session + create new
        Returns { session_id }
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
        """GET /api/v1/consumer/course/classrooms/{uid}/ai-sessions/
        List all sessions for this user in this classroom.
        """
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        sessions = _ai_session_service.list_sessions(
            user_id=request.user.uid, classroom_id=str(pk)
        )
        return Response(sessions)

    @action(detail=True, methods=['get'], url_path='ai-session/history')
    def ai_session_history(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/ai-session/history/?session_id=xxx"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        session_id = (request.query_params.get('session_id') or '').strip()
        if not session_id or not _ai_session_service.session_exists(session_id):
            return Response({'error': 'Session không hợp lệ.'}, status=status.HTTP_404_NOT_FOUND)
        messages = _ai_session_service.get_display_messages(session_id)
        return Response({'session_id': session_id, 'messages': messages})
