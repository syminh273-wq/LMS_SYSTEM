import json
import uuid

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.serializers.classroom import ClassroomResponseSerializer
from core.serializers.classroom.request import ClassroomRequestSerializer
from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import UserScopeMixin
from features.account.space.models.space import Space
from features.chat.serializers.conversation_serializer import ConversationSerializer
from features.chat.services.conversation_service import ConversationService
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_doc_service import ClassroomDocService
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
            if result.get('success'):
                return Response(
                    ResourceResponseSerializer(result['data']).data,
                    status=status.HTTP_201_CREATED,
                )
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
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=['post'], url_path='ask')
    def ask(self, request, uid=None):
        """POST /classrooms/{uid}/ask/ — synchronous RAG Q&A against classroom docs."""
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        section = request.data.get('section') or None
        top_k = min(int(request.data.get('top_k', 5)), 10)

        pipeline = RAGPipeline()
        filter_meta = {'classroom_id': str(uid)}
        if section:
            filter_meta['section'] = section
        
        result = pipeline.ask(question, top_k=top_k, filter_meta=filter_meta,
                              system_prompt=self._CLASSROOM_PROMPT)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='ask-stream')
    def ask_stream(self, request, uid=None):
        """POST /classrooms/{uid}/ask-stream/ — SSE streaming RAG Q&A."""
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Câu hỏi không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        section = request.data.get('section') or None
        top_k = min(int(request.data.get('top_k', 5)), 10)

        pipeline = RAGPipeline()
        filter_meta = {'classroom_id': str(uid)}
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
