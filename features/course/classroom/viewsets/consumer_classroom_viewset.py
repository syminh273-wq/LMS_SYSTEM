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

    @action(detail=False, methods=['get'], url_path='by-teacher')
    def by_teacher(self, request):
        """GET /api/v1/consumer/course/classrooms/by-teacher/?teacher_id=<uid>

        Lightweight, public-safe listing for a teacher profile page. Returns
        only `active` + `public` classrooms (visibility_type='public'), sorted
        newest first. No teacher-only fields are exposed.
        """
        teacher_id_raw = (request.query_params.get('teacher_id') or '').strip()
        if not teacher_id_raw:
            return Response({'error': 'teacher_id là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            teacher_uuid = uuid.UUID(teacher_id_raw)
        except (ValueError, TypeError):
            return Response({'error': 'teacher_id không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = list(Service().get_by_teacher(teacher_uuid))
        except Exception:
            rows = []

        results = []
        for c in rows:
            if getattr(c, 'is_deleted', False):
                continue
            if getattr(c, 'status', 'active') != 'active':
                continue
            if getattr(c, 'visibility_type', 'public') != 'public':
                continue
            data = ClassroomResponseSerializer(c).data
            keep = {
                'uid': data.get('uid'),
                'name': data.get('name'),
                'description': data.get('description'),
                'category': data.get('category'),
                'pricing_type': data.get('pricing_type'),
                'price_vnd': data.get('price_vnd'),
                'max_students': data.get('max_students'),
                'preview_folder_uid': data.get('preview_folder_uid'),
                'created_at': data.get('created_at'),
            }
            results.append(keep)

        results.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
        return Response(results)

    @action(detail=False, methods=['get'], url_path='discover')
    def discover(self, request):
        """GET /api/v1/consumer/course/classrooms/discover/

        Public classroom catalog for the consumer Discover page.
        Query params:
            category    (optional) — math, physics, ... see CATEGORY_CHOICES
            pricing_type (optional) — 'free' or 'paid'
            search      (optional) — substring match on name + description
        """
        category = (request.query_params.get('category') or '').strip().lower() or None
        pricing_type = (request.query_params.get('pricing_type') or '').strip().lower() or None
        search = (request.query_params.get('search') or '').strip() or None

        if pricing_type and pricing_type not in ('free', 'paid'):
            return Response({'error': 'pricing_type không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        classrooms = list(Service().list_discoverable(
            category=category,
            pricing_type=pricing_type,
            search=search,
        ))

        joined_uids = set(str(u) for u in ClassroomMemberService().get_joined_classroom_uids(request.user.uid))

        member_repo = ClassroomMemberRepository()
        from features.social.services.classroom_favorite_service import ClassroomFavoriteService
        fav_service = ClassroomFavoriteService()
        results = []
        for c in classrooms:
            data = ClassroomResponseSerializer(c).data
            data['is_joined'] = str(c.uid) in joined_uids
            member = member_repo.get_member(c.uid, request.user.uid)
            if member and not member.is_deleted:
                data['membership_status'] = member.status
                data['has_paid'] = bool(getattr(member, 'has_paid', False))
            else:
                data['membership_status'] = None
                data['has_paid'] = False
            data['is_favorited'] = fav_service.is_favorited(request.user.uid, c.uid)
            data['favorite_count'] = fav_service.favorite_count(c.uid)
            results.append(data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(results, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response(results)

    @action(detail=False, methods=['post'], url_path='quick-join')
    def quick_join(self, request):
        """POST /api/v1/consumer/course/classrooms/quick-join/  body: {classroom_uid}

        Public-classroom quick join. Returns the same shape as `join_by_code`:
            Free  → { joined: true, classroom_uid, membership_status: 'approved' }
            Paid  → { requires_payment: true, pay_url, order_id, amount, classroom_uid }
            Private → 403
            Already member → { joined: true, classroom_uid, membership_status: 'approved' }
        """
        from features.course.classroom.repositories import Repository as ClassroomRepo
        from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService

        classroom_uid_raw = (request.data.get('classroom_uid') or '').strip()
        if not classroom_uid_raw:
            return Response({'error': 'classroom_uid là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            classroom_uuid = uuid.UUID(classroom_uid_raw)
        except ValueError:
            return Response({'error': 'classroom_uid không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            classroom = ClassroomRepo().find(str(classroom_uuid))
        except Exception:
            return Response({'error': 'Lớp học không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        if getattr(classroom, 'status', 'active') != 'active':
            return Response({'error': 'Lớp học không khả dụng.'}, status=status.HTTP_403_FORBIDDEN)

        if getattr(classroom, 'visibility_type', 'public') != 'public':
            return Response(
                {'error': 'Lớp học này ở chế độ riêng tư. Vui lòng dùng mã mời.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if ClassroomBlacklistService().is_blocked(classroom.uid, classroom.teacher_id, request.user.uid):
            return Response({'error': 'Bạn đã bị chặn khỏi lớp học này.'}, status=status.HTTP_403_FORBIDDEN)

        existing = ClassroomMemberService().is_member(classroom.uid, request.user.uid)
        if existing:
            member = ClassroomMemberRepository().get_member(classroom.uid, request.user.uid)
            return Response({
                'joined': True,
                'requires_payment': False,
                'membership_status': getattr(member, 'status', 'approved') if member else 'approved',
                'classroom_uid': str(classroom.uid),
            })

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
                'joined': False,
                'requires_payment': True,
                'membership_status': 'pending',
                'classroom_uid': str(classroom.uid),
                'amount': int(classroom.price_vnd or 0),
                **result,
            })

        member = ClassroomMemberService().join(classroom_uid=classroom.uid, user=request.user, role='student')
        return Response({
            'joined': True,
            'requires_payment': False,
            'membership_status': getattr(member, 'status', 'pending'),
            'classroom_uid': str(classroom.uid),
        })

    def retrieve(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/"""
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        from features.social.services.classroom_favorite_service import ClassroomFavoriteService
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

        fav_service = ClassroomFavoriteService()
        is_favorited = fav_service.is_favorited(request.user.uid, instance.uid)
        favorite_count = fav_service.favorite_count(instance.uid)

        if is_paid_classroom and not has_paid:
            data = ClassroomResponseSerializer(instance).data
            data['has_access'] = False
            data['has_paid'] = has_paid
            data['requires_payment'] = True
            data['join_required'] = True
            data['membership_status'] = getattr(member, 'status', None) if member else None
            data['is_favorited'] = is_favorited
            data['favorite_count'] = favorite_count
            return Response(data)

        if member and not member.is_deleted and member.status == 'pending':
            data = ClassroomResponseSerializer(instance).data
            data['has_access'] = False
            data['has_paid'] = bool(getattr(member, 'has_paid', False))
            data['requires_payment'] = False
            data['join_required'] = False
            data['membership_status'] = 'pending'
            data['is_favorited'] = is_favorited
            data['favorite_count'] = favorite_count
            return Response(data)

        if not member or member.is_deleted:
            data = ClassroomResponseSerializer(instance).data
            data['has_access'] = False
            data['has_paid'] = False
            data['requires_payment'] = is_paid_classroom
            data['join_required'] = True
            data['membership_status'] = None
            data['is_favorited'] = is_favorited
            data['favorite_count'] = favorite_count
            return Response(data)

        data = ClassroomResponseSerializer(instance).data
        data['has_access'] = True
        data['has_paid'] = has_paid
        data['requires_payment'] = False
        data['join_required'] = False
        data['membership_status'] = 'approved'
        data['is_favorited'] = is_favorited
        data['favorite_count'] = favorite_count
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
        """POST /api/v1/consumer/course/classrooms/{uid}/checkout/ — initiate MoMo for a paid classroom.

        Member + teacher notification are deferred to the MoMo IPN success path
        (`ClassroomMemberService.mark_paid_pending`). This endpoint only ensures
        a PENDING payment exists and returns the MoMo pay_url.
        """
        from features.course.classroom.repositories import Repository
        from features.payment.enums import PaymentStatus
        from features.payment.repositories import PaymentRepository
        from features.payment.services import PaymentService
        import base64
        import json

        try:
            classroom = Repository().find(str(pk))
        except Exception:
            return Response({'error': 'Lớp học không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        if getattr(classroom, 'pricing_type', 'free') != 'paid':
            return Response({'error': 'Lớp học này miễn phí, không cần thanh toán.'}, status=status.HTTP_400_BAD_REQUEST)
        if int(classroom.price_vnd or 0) < 1000:
            return Response({'error': 'Giá lớp học không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            for p in PaymentRepository().get_by_consumer(str(request.user.uid)):
                if p.status != PaymentStatus.PENDING.value:
                    continue
                try:
                    meta = json.loads(base64.b64decode(p.extra_data).decode())
                except Exception:
                    continue
                if (meta.get('resource_type') == 'classroom'
                        and meta.get('resource_id') == str(classroom.uid)):
                    return Response({
                        'classroom_uid': str(classroom.uid),
                        'amount': int(p.amount or 0),
                        'order_id': p.order_id,
                        'pay_url': p.pay_url,
                    })
        except Exception:
            pass

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

    @action(detail=True, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/leaderboard/?limit=10

        Returns top-N students in the classroom plus the caller's rank.
        Only approved members of the classroom can view.
        """
        from features.course.classroom.services.leaderboard_service import LeaderboardService

        if not ClassroomMemberService().is_member(str(pk), request.user.uid):
            return Response(
                {'error': 'Bạn cần tham gia lớp để xem bảng xếp hạng.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            limit = int(request.query_params.get('limit', 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 100))

        payload = LeaderboardService().build(
            classroom_id=str(pk),
            current_user_id=str(request.user.uid),
            limit=limit,
        )
        return Response(payload)

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

    @action(detail=True, methods=['get'], url_path='preview')
    def preview(self, request, pk=None):
        """GET /api/v1/consumer/course/classrooms/{uid}/preview/

        Landing page payload: classroom info, preview folder + docs, and the
        action the consumer should take (join / checkout / none).
        """
        from features.course.classroom.services.classroom_doc_service import ClassroomDocService
        from features.course.classroom.repositories import Repository as ClassroomRepo
        from features.course.classroom.services.classroom_blacklist_service import ClassroomBlacklistService

        try:
            classroom = ClassroomRepo().find(str(pk))
        except Exception:
            return Response({'error': 'Lớp học không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        if getattr(classroom, 'is_deleted', False) or getattr(classroom, 'status', 'active') != 'active':
            return Response({'error': 'Lớp học không khả dụng.'}, status=status.HTTP_403_FORBIDDEN)

        is_member_approved = False
        if request.user and getattr(request.user, 'uid', None) is not None:
            if ClassroomBlacklistService().is_blocked(classroom.uid, classroom.teacher_id, request.user.uid):
                return Response({'error': 'Bạn đã bị chặn khỏi lớp học này.'}, status=status.HTTP_403_FORBIDDEN)
            member = ClassroomMemberRepository().get_member(classroom.uid, request.user.uid)
            is_member_approved = bool(member and not member.is_deleted and member.status == 'approved')

        if not is_member_approved and getattr(classroom, 'visibility_type', 'public') == 'private':
            return Response(
                {'error': 'Lớp học này ở chế độ riêng tư. Vui lòng dùng mã mời.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        consumer_id = str(request.user.uid) if request.user and getattr(request.user, 'uid', None) is not None else None
        payload = Service().get_preview_for_consumer(classroom.uid, consumer_id=consumer_id)
        return Response(payload)

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
