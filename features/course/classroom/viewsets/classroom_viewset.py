import base64
import json
import uuid

from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from features.ai.services.ai_conversation_session_service import AIConversationSessionService

_ai_session_service = AIConversationSessionService()
from core.serializers.classroom import ClassroomResponseSerializer
from core.serializers.classroom.request import ClassroomRequestSerializer
from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.space.models.space import Space
from features.chat.serializers.conversation_serializer import ConversationSerializer
from features.chat.services.conversation_service import ConversationService
from features.course.classroom.services import Service, ClassroomAIService
from features.course.classroom.services.classroom_doc_service import ClassroomDocService
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService
from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer
from features.sharing.serializers.link_response_serializer import LinkResponseSerializer
from features.sharing.services import LinkService

class ClassroomViewSet(UserScopeMixin, BaseModelViewSet):
    serializer_class = ClassroomResponseSerializer

    def get_queryset(self):
        if isinstance(self.request.user, Space):
            return Service().get_by_teacher(self.request.user.uid)
        return Service().get_active_classrooms()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = Service().find(kwargs['uid'])
        return Response(ClassroomResponseSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        # Only teachers (Space accounts) can create a classroom
        if not isinstance(request.user, Space):
            raise PermissionDenied("Only teachers (Space accounts) can create a classroom.")

        serializer = ClassroomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Service().create_classroom(
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        ClassroomActivityLogService().log(
            classroom_uid=instance.uid,
            log_level='major',
            event_type='classroom_created',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_name=instance.name,
        )
        return Response(ClassroomResponseSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        
        # Ownership check
        if not isinstance(request.user, Space) or instance.teacher_id != request.user.uid:
            raise PermissionDenied("You do not have permission to update this classroom.")

        serializer = ClassroomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = service.update(instance, **serializer.validated_data)
        return Response(ClassroomResponseSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])
        
        # Ownership check
        if not isinstance(request.user, Space) or instance.teacher_id != request.user.uid:
            raise PermissionDenied("You do not have permission to delete this classroom.")

        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def conversation(self, request, uid=None):
        """Return (or auto-create) the channel conversation for this classroom."""
        conv = ConversationService().get_or_create_channel(
            classroom_uid=uuid.UUID(str(uid)),
            created_by_id=request.user.uid,
        )
        return Response(ConversationSerializer(conv).data)

    @action(detail=True, methods=['get'])
    def sharing_link(self, request, uid=None):
        classroom = Service().find(uid)
        link_service = LinkService()
        
        # Find link by resource_id
        links = link_service.repository.get_by_resource('classroom', classroom.uid)
        link = links.first() if links else None
        
        if not link:
            # Fallback: create one if missing for some reason
            link = link_service.create_link({
                'code': classroom.pid,
                'resource_type': 'classroom',
                'resource_id': classroom.uid,
                'action': 'join',
                'metadata': {'name': classroom.name}
            })

        # Lazy load QR
        link_service.get_or_create_qr_code(link)

        return Response(LinkResponseSerializer(link).data)

    # ── Documents (LanceDB) ───────────────────────────────────────────────────

    @action(detail=True, methods=['post', 'get'], url_path='docs')
    def docs(self, request, uid=None):
        """
        POST /classrooms/{uid}/docs/  — upload a document and index it in LanceDB.
          Form fields:
            file     (required) — PDF, TXT, or MD
            section  (optional) — category label, e.g. "week1", "lecture", …

        GET  /classrooms/{uid}/docs/  — list all documents for this classroom.
          Query params:
            section  (optional) — filter by section label
        """
        doc_service = ClassroomDocService()

        if request.method == 'POST':
            if not isinstance(request.user, Space):
                raise PermissionDenied("Only teachers can upload documents.")

            if 'file' not in request.FILES:
                return Response(
                    {'success': False, 'message': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            section = request.data.get('section', '')
            result = doc_service.upload_and_index(
                classroom_uid=str(uid),
                file_obj=request.FILES['file'],
                section=section,
            )
            resource = result.get('data')
            if resource:
                ClassroomActivityLogService().log(
                    classroom_uid=uid,
                    log_level='major',
                    event_type='document_uploaded',
                    actor_id=request.user.uid,
                    actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                    actor_role='teacher',
                    target_name=getattr(resource, 'name', ''),
                    metadata={'section': section},
                )
                resp_data = ResourceResponseSerializer(resource).data
                if not result.get('success'):
                    # File uploaded to R2 but LanceDB indexing failed — warn the client
                    resp_data['_warning'] = result.get('message', 'LanceDB indexing thất bại')
                return Response(resp_data, status=status.HTTP_201_CREATED)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # GET
        section = request.query_params.get('section')
        docs = doc_service.list_docs(classroom_uid=str(uid), section=section)
        return Response(ResourceResponseSerializer(docs, many=True).data)

    def docs_delete(self, request, uid=None, resource_uid=None):
        """DELETE /classrooms/{uid}/docs/{resource_uid}/"""
        if not isinstance(request.user, Space):
            raise PermissionDenied("Only teachers can delete documents.")

        result = ClassroomDocService().delete_doc(
            classroom_uid=str(uid),
            resource_uid=resource_uid,
        )
        if result.get('success'):
            ClassroomActivityLogService().log(
                classroom_uid=uid,
                log_level='detail',
                event_type='document_deleted',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=resource_uid,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    # ── Activity Log ─────────────────────────────────────────────────────────

    @action(detail=True, methods=['get'], url_path='activity')
    def activity(self, request, uid=None):
        """
        GET /classrooms/{uid}/activity/
          ?level=major|detail   (default: major)
          &limit=50
          &before=<iso_datetime>
        """
        from datetime import datetime as dt
        log_level = request.query_params.get('level', 'major')
        limit = min(int(request.query_params.get('limit', 50)), 200)
        before_str = request.query_params.get('before')
        before = None
        if before_str:
            try:
                before = dt.fromisoformat(before_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        logs = ClassroomActivityLogService().list(
            classroom_uid=uid,
            log_level=log_level if log_level in ('major', 'detail') else None,
            limit=limit,
            before=before,
        )
        return Response(logs)

    # ── AI Bot ────────────────────────────────────────────────────────────────

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

    @action(detail=True, methods=['post'], url_path='ask')
    def ask(self, request, uid=None):
        """POST /classrooms/{uid}/ask/ — synchronous RAG Q&A against classroom docs."""
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
            system_prompt=self._CLASSROOM_PROMPT
        )

        return Response({
            'answer':     result['answer'],
            'tool_calls': result['tool_calls'],
            'session_id': session_id,
        })

    @action(detail=True, methods=['post'], url_path='ask-stream')
    def ask_stream(self, request, uid=None):
        """POST /classrooms/{uid}/ask-stream/ — SSE streaming RAG Q&A."""
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

        session_id = ai_service.get_session_id(
            request.data.get('session_id'), request.user.uid, uid
        )

        mode = (request.data.get('mode') or 'doc').strip()
        section = request.data.get('section')

        resp = StreamingHttpResponse(
            ai_service.ask_stream(
                question=question,
                session_id=session_id,
                user_id=request.user.uid,
                classroom_id=uid,
                mode=mode,
                section=section
            ),
            content_type='text/event-stream; charset=utf-8'
        )
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp

    @action(detail=True, methods=['post'], url_path='tts')
    def tts(self, request, uid=None):
        """POST /classrooms/{uid}/tts/ — convert text answer to MP3 audio."""
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'error': 'text không được để trống'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mp3_bytes = ClassroomAIService().synthesize_text(text)
        except Exception as exc:
            return Response({'error': f'TTS thất bại: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return HttpResponse(mp3_bytes, content_type='audio/mpeg')

    @action(detail=True, methods=['get'], url_path='active-session')
    def active_session(self, request, uid=None):
        """GET /classrooms/{uid}/active-session/
        Automatically continue the most recent session or create a new one.
        """
        session_id = _ai_session_service.ensure_session(None, request.user.uid, str(uid))
        messages = _ai_session_service.get_display_messages(session_id)
        return Response({
            'session_id': session_id,
            'messages': messages
        })

    @action(detail=True, methods=['post'], url_path='ai-session')
    def ai_session(self, request, uid=None):
        """POST /classrooms/{uid}/ai-session/
        Create new session or clear existing one.
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
        """GET /classrooms/{uid}/ai-sessions/
        List all AI sessions for this teacher in this classroom.
        """
        sessions = _ai_session_service.list_sessions(
            user_id=request.user.uid, classroom_id=str(uid)
        )
        return Response(sessions)

    @action(detail=True, methods=['get'], url_path='ai-session/history')
    def ai_session_history(self, request, uid=None):
        """GET /classrooms/{uid}/ai-session/history/?session_id=xxx"""
        session_id = (request.query_params.get('session_id') or '').strip()
        if not session_id or not _ai_session_service.session_exists(session_id):
            return Response({'error': 'Session không hợp lệ.'}, status=status.HTTP_404_NOT_FOUND)
        messages = _ai_session_service.get_display_messages(session_id)
        return Response({'session_id': session_id, 'messages': messages})
