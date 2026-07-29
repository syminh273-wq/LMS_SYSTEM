import json
import uuid

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.serializers.classroom import ClassroomResponseSerializer
from core.views.api.pagination import StandardResultsSetPagination
from core.views.mixins import ConsumerScopeMixin
from features.chat.serializers.conversation_serializer import ConversationSerializer
from features.chat.services.conversation_service import ConversationService
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_member_service import ClassroomMemberService


class ConsumerClassroomViewSet(ConsumerScopeMixin, ViewSet):
    """Classroom endpoints for students (Consumer accounts)."""

    pagination_class = StandardResultsSetPagination

    def list(self, request):
        """
        List classrooms the current student has joined.
        @return: joined classrooms
        """
        uids = ClassroomMemberService().get_joined_classroom_uids(request.user.uid)
        service = Service()
        classrooms = []
        for uid in uids:
            try:
                classroom = service.find(str(uid))
                if getattr(classroom, 'visibility_type', 'public') == 'private':
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
        """
        List a teacher's public, active classrooms for their public profile page.
        @param teacher_id: teacher uid
        @return: public-safe classroom summaries, newest first
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
        """
        List public classrooms for the consumer Discover catalog.
        @param category: filter by category (optional)
        @param pricing_type: 'free' or 'paid' (optional)
        @param search: substring match on name/description (optional)
        @return: discoverable classrooms
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
        """
        Join a public classroom without an invite code.
        @param classroom_uid: the classroom to join
        @return: join result — joined status, or payment info if the classroom is paid
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
        """
        Get a classroom's detail, scoped to the current student's access/membership.
        @return: classroom detail with access/membership flags
        """
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        from features.social.services.classroom_favorite_service import ClassroomFavoriteService
        import uuid as _uuid
        try:
            classroom_uid = _uuid.UUID(str(pk))
        except ValueError:
            return Response({'error': 'ID lớp không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        instance = Service().find(pk)
        if getattr(instance, 'visibility_type', 'public') == 'private':
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
        """
        Join a classroom using its invite code.
        @param code: the classroom invite code
        @return: join result
        """
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
        """
        Initiate MoMo payment for a paid classroom.

        Member + teacher notification are deferred to the MoMo IPN success path
        (`ClassroomMemberService.mark_paid_pending`). This endpoint only ensures
        a PENDING payment exists and returns the MoMo pay_url.
        @return: classroom_uid, amount, pay_url, order_id
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
        """
        Poll access status for a classroom during the checkout flow.
        @return: access status
        """
        return Response(Service().get_access_for_consumer(str(pk), consumer_id=str(request.user.uid)))

    @action(detail=False, methods=['get'], url_path='me/history')
    def me_history(self, request):
        """
        List every join event the current student has with any classroom, newest first.
        @param limit: max entries, default 50
        @return: join history, including soft-deleted and rejected entries
        """
        from features.course.classroom.serializers.classroom_member_history_serializer import ClassroomMemberHistorySerializer
        try:
            limit = int(request.query_params.get('limit') or 50)
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 200))

        members = list(ClassroomMemberRepository().get_history_by_member(request.user.uid, limit=limit))
        members.sort(key=lambda m: getattr(m, 'joined_at', None) or getattr(m, 'updated_at', None) or 0, reverse=True)

        service = Service()
        items = []
        for m in members:
            classroom_name = ''
            teacher_name = ''
            try:
                c = service.find(str(m.classroom_uid))
                classroom_name = getattr(c, 'name', '') or ''
                teacher_name = getattr(c, 'teacher_name', '') or ''
            except Exception:
                pass
            items.append(ClassroomMemberHistorySerializer(
                m,
                context={'classroom_name': classroom_name, 'teacher_name': teacher_name},
            ).data)
        return Response(items)

    @action(detail=True, methods=['get'], url_path='preview-folder')
    def preview_folder(self, request, pk=None):
        """
        Get the preview folder and its documents for a classroom. Always accessible.
        @return: folder, docs
        """
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
        """
        Get the classroom landing-page payload for a prospective student.
        @return: classroom info, preview folder + docs, next action (join/checkout/none)
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
        """
        Get (or auto-create) the channel conversation for this classroom.
        @return: conversation
        """
        conv = ConversationService().get_or_create_channel(
            classroom_uid=uuid.UUID(str(pk)),
            created_by_id=request.user.uid,
        )
        return Response(ConversationSerializer(conv).data)

    def _check_member(self, classroom_uid, user_uid):
        member = ClassroomMemberRepository().get_member(uuid.UUID(str(classroom_uid)), user_uid)
        if not member or member.is_deleted or member.status != 'approved':
            return False
        return True

    @action(detail=True, methods=['get'], url_path='docs')
    def docs(self, request, pk=None):
        """
        List documents for a classroom the student is a member of.
        @param section: filter by section (optional)
        @param folder_id: filter by folder (optional)
        @return: documents
        """
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
        """
        List folder tree and documents, scoped to the student's paid access.

        Paid + non-member → only preview folder + preview docs.
        Paid + member   → full tree.
        Free            → full tree (no member check).
        @return: folders, root docs, preview_only flag
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
