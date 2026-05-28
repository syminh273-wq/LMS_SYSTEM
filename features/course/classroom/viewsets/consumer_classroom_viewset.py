import json
import uuid

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.serializers.classroom import ClassroomResponseSerializer
from core.views.api.pagination import StandardResultsSetPagination
from core.views.mixins import UserScopeMixin
from features.chat.serializers.conversation_serializer import ConversationSerializer
from features.chat.services.conversation_service import ConversationService
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_member_service import ClassroomMemberService


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
                classrooms.append(service.find(str(uid)))
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

        member = ClassroomMemberRepository().get_member(classroom_uid, request.user.uid)
        if not member or member.is_deleted:
            return Response({'error': 'Bạn chưa đăng ký tham gia lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        if member.status == 'pending':
            return Response(
                {'error': 'Yêu cầu của bạn đang chờ giáo viên phê duyệt.', 'membership_status': 'pending'},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = Service().find(pk)
        return Response(ClassroomResponseSerializer(instance).data)

    @action(detail=False, methods=['post'], url_path='join')
    def join_by_code(self, request):
        """POST /api/v1/consumer/course/classrooms/join/  body: {"code": "ABCDEF"}"""
        code = (request.data.get('code') or '').strip().upper()
        if not code:
            return Response({'error': 'Mã lớp không được để trống.'}, status=status.HTTP_400_BAD_REQUEST)

        from features.course.classroom.repositories import Repository
        classroom = Repository().filter(pid=code).first()
        if not classroom or getattr(classroom, 'is_deleted', False) or classroom.status != 'active':
            return Response({'error': 'Mã lớp không hợp lệ hoặc lớp không còn hoạt động.'}, status=status.HTTP_404_NOT_FOUND)

        member = ClassroomMemberService().join(classroom_uid=classroom.uid, user=request.user, role='student')
        return Response(
            {'membership_status': getattr(member, 'status', 'pending')},
            status=status.HTTP_200_OK,
        )

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
        "Bạn là AI Trợ giảng, hỗ trợ học sinh và giáo viên hiểu sâu nội dung bài học.\n\n"
        "Khi trả lời, hãy tuân theo các nguyên tắc sau:\n"
        "1. Trả lời đầy đủ và có chiều sâu — giải thích để người học thực sự hiểu, không chỉ tóm tắt lướt qua.\n"
        "2. Dẫn chứng cụ thể từ tài liệu — trích ý chính, ví dụ hoặc định nghĩa từ ngữ liệu. "
        "Dùng câu như \"Theo tài liệu...\", \"Bài học nêu rõ rằng...\", \"Ví dụ được đưa ra là...\".\n"
        "3. Văn phong tự nhiên, thân thiện — viết như người thầy đang giảng cho học sinh, "
        "không cứng nhắc như sách giáo khoa. Có thể dùng ví dụ thực tế để minh họa thêm.\n"
        "4. Cấu trúc rõ ràng — nếu có nhiều ý, chia thành đoạn văn riêng hoặc liệt kê có thứ tự.\n"
        "5. CHỈ dựa vào tài liệu lớp học được cung cấp — tuyệt đối không dùng kiến thức bên ngoài "
        "hay tự bịa thêm thông tin.\n"
        "6. Nếu tài liệu không có đủ thông tin để trả lời chính xác, CHỈ nói duy nhất câu sau "
        "và không thêm bất kỳ lời giải thích hay gợi ý nào khác: 'Tài liệu lớp học không có thông tin về vấn đề này.'\n"
        "7. Đối với lời chào hoặc hội thoại xã giao (như 'Xin chào', 'Hi', 'Hello', 'Chào bạn',...): CHỈ chào lại ngắn gọn và hỏi xem có thể giúp gì được không. Tuyệt đối CẤM nhắc đến bất kỳ từ khóa, chủ đề, tên nhân vật hay nội dung nào có trong tài liệu (như 'Bác Hồ', 'giản dị', 'tiết kiệm',...) trong lời chào này.\n\n"
        "Tài liệu lớp học (căn cứ trả lời):\n{context}\n\n"
        "CHỈ trả lời bằng tiếng Việt. Tuyệt đối không trả lời bằng tiếng Anh hay bất kỳ ngôn ngữ nào khác trừ khi người dùng yêu cầu cụ thể."
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
        section = request.data.get('section') or None
        top_k = min(int(request.data.get('top_k', 5)), 10)

        pipeline = RAGPipeline()
        filter_meta = {'classroom_id': str(pk)}
        if section:
            filter_meta['section'] = section
        
        result = pipeline.ask(question, top_k=top_k, filter_meta=filter_meta,
                              system_prompt=self._CLASSROOM_PROMPT)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='ask-stream')
    def ask_stream(self, request, pk=None):
        """POST /api/v1/consumer/course/classrooms/{uid}/ask-stream/"""
        if not self._check_member(pk, request.user.uid):
            return Response({'error': 'Bạn chưa là thành viên của lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        section = request.data.get('section') or None
        top_k = min(int(request.data.get('top_k', 5)), 10)

        pipeline = RAGPipeline()
        filter_meta = {'classroom_id': str(pk)}
        if section:
            filter_meta['section'] = section

        def _generate():
            try:
                for chunk in pipeline.ask_stream(question, top_k=top_k, filter_meta=filter_meta,
                                                 system_prompt=self._CLASSROOM_PROMPT):
                    if isinstance(chunk, tuple):
                        signal, data = chunk
                        if signal == '__SOURCES__':
                            payload = json.dumps({'type': 'sources', 'data': data}, ensure_ascii=False)
                        elif signal == '__ERROR__':
                            payload = json.dumps({'type': 'error', 'message': str(data)}, ensure_ascii=False)
                        else:
                            continue
                    else:
                        payload = json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)
                    yield f'data: {payload}\n\n'
            except Exception as exc:
                yield f'data: {json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)}\n\n'
            finally:
                yield 'data: [DONE]\n\n'

        resp = StreamingHttpResponse(_generate(), content_type='text/event-stream; charset=utf-8')
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
        docs = ClassroomDocService().list_docs(classroom_uid=str(pk))
        return Response(ResourceResponseSerializer(docs, many=True).data)
