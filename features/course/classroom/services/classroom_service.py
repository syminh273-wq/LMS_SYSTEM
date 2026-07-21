import string
import random
from features.course.classroom.repositories import Repository
from features.sharing.services import LinkService
from features.sharing.enums import ResourceType
from core.search_engine.typesense.indexer import LMSIndexer

class Service:
    def __init__(self):
        self.repository = Repository()
        self.link_service = LinkService()

    def all(self):
        return self.repository.all()

    def find(self, uid):
        return self.repository.find(uid)

    def get_active_classrooms(self):
        return self.repository.get_active_classrooms()

    def get_by_teacher(self, teacher_id):
        return self.repository.get_by_teacher(teacher_id)

    def list_discoverable(self, *, category=None, pricing_type=None, search=None):
        return self.repository.discover(
            category=category or None,
            pricing_type=pricing_type or None,
            visibility_type='public',
            search=search or None,
        )

    def create_classroom(self, teacher_id, data: dict):
        # Generate a unique 6-char uppercase alphanumeric pid (invite code)
        pid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        classroom = self.repository.create(teacher_id=teacher_id, pid=pid, **data)

        # Create a short link for this classroom
        self.link_service.create_link({
            'code': pid,
            'resource_type': ResourceType.CLASSROOM.value,
            'resource_id': classroom.uid,
            'action': 'join',
            'metadata': {
                'name': classroom.name
            }
        })

        # Auto-create a Preview folder so the new flow has a default free tab
        try:
            from features.resource.services.resource_folder_service import ResourceFolderService
            ResourceFolderService().ensure_preview_folder(classroom.uid, teacher_id)
        except Exception as exc:
            print(f"[ClassroomService] Failed to auto-create preview folder: {exc}")

        LMSIndexer.index_classroom(classroom)
        return classroom

    def update(self, instance, **kwargs):
        updated = self.repository.update(instance, **kwargs)
        LMSIndexer.index_classroom(updated)
        return updated

    def delete(self, instance):
        result = self.repository.delete(instance)
        LMSIndexer.remove_classroom(str(instance.uid))
        return result

    def get_access_for_consumer(self, classroom_uid, consumer_id=None):
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        from features.payment.repositories import PaymentRepository
        from features.payment.enums import PaymentStatus
        import base64
        import json

        classroom = self.find(str(classroom_uid))
        pricing_type = getattr(classroom, 'pricing_type', 'free') or 'free'
        is_paid_classroom = pricing_type == 'paid'

        has_paid = False
        membership_status = None
        classroom_uid_str = str(classroom_uid)

        if consumer_id is not None:
            member = ClassroomMemberRepository().get_member(classroom_uid, consumer_id)
            if member and not member.is_deleted:
                has_paid = bool(getattr(member, 'has_paid', False)) and member.status == 'approved'
                membership_status = member.status

        pending_payment = None
        if consumer_id is not None and is_paid_classroom and not has_paid:
            try:
                payments = PaymentRepository().get_by_consumer(consumer_id)
                for p in payments:
                    if p.status != PaymentStatus.PENDING.value:
                        continue
                    try:
                        meta = json.loads(base64.b64decode(p.extra_data).decode())
                    except Exception:
                        continue
                    if meta.get('resource_type') == 'classroom' and meta.get('resource_id') == classroom_uid_str:
                        pending_payment = {
                            'order_id': p.order_id,
                            'pay_url': p.pay_url,
                            'amount': int(p.amount or 0),
                        }
                        break
            except Exception:
                pass

        return {
            'classroom_uid': classroom_uid_str,
            'pricing_type': pricing_type,
            'is_paid_classroom': is_paid_classroom,
            'has_access': (not is_paid_classroom) or has_paid,
            'has_paid': has_paid,
            'membership_status': membership_status,
            'pending_payment': pending_payment,
        }

    def get_preview_for_consumer(self, classroom_uid, consumer_id=None):
        """Build the data payload for the consumer preview page.

        Returns a dict with:
            classroom      — full ClassroomResponseSerializer data + favorite info
            preview        — {folder, docs} for the preview folder
            actions        — {type, requires_payment, membership_status, pay_url?, amount?}
            is_favorited   — bool (only when consumer_id is provided)
            favorite_count — int
        """
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        from features.course.classroom.services.classroom_doc_service import ClassroomDocService
        from features.resource.serializers.resource_folder_serializer import ResourceFolderResponseSerializer
        from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer
        from features.social.services.classroom_favorite_service import ClassroomFavoriteService
        from core.serializers.classroom.classroom_response_serializer import ClassroomResponseSerializer

        classroom = self.find(str(classroom_uid))
        pricing_type = getattr(classroom, 'pricing_type', 'free') or 'free'
        is_paid_classroom = pricing_type == 'paid'

        member = None
        has_paid = False
        membership_status = None
        approved = False
        if consumer_id is not None:
            try:
                member = ClassroomMemberRepository().get_member(classroom.uid, consumer_id)
                if member and not member.is_deleted:
                    has_paid = bool(getattr(member, 'has_paid', False)) and member.status == 'approved'
                    membership_status = member.status
                    approved = member.status == 'approved'
            except Exception:
                pass

        if approved:
            action_type = 'none'
        elif is_paid_classroom and not has_paid:
            action_type = 'checkout'
        else:
            action_type = 'join'

        pay_url = None
        pending_payment = None
        amount = int(classroom.price_vnd or 0)
        if action_type == 'checkout':
            try:
                from features.payment.repositories import PaymentRepository
                from features.payment.enums import PaymentStatus
                import base64
                import json

                for p in PaymentRepository().get_by_consumer(str(consumer_id)):
                    if p.status != PaymentStatus.PENDING.value:
                        continue
                    try:
                        meta = json.loads(base64.b64decode(p.extra_data).decode())
                    except Exception:
                        continue
                    if (meta.get('resource_type') == 'classroom'
                            and meta.get('resource_id') == str(classroom.uid)):
                        pending_payment = {
                            'order_id': p.order_id,
                            'pay_url': p.pay_url,
                            'amount': int(p.amount or 0),
                        }
                        break
            except Exception:
                pass

            if pending_payment:
                pay_url = pending_payment.get('pay_url')
                amount = pending_payment.get('amount') or amount
            else:
                try:
                    from features.payment.services import PaymentService
                    init = PaymentService().initiate(
                        consumer_id=str(consumer_id),
                        amount=amount,
                        order_info=f'Lớp học: {classroom.name}',
                        resource_type='classroom',
                        resource_id=str(classroom.uid),
                    )
                    pay_url = init.get('pay_url')
                except Exception:
                    pay_url = None

        preview_folder = ClassroomDocService().get_preview_folder(str(classroom.uid))
        if preview_folder is not None:
            folder_payload = ResourceFolderResponseSerializer(preview_folder).data
            root_docs = ClassroomDocService().list_folder(
                classroom_uid=str(classroom.uid), folder_id=str(preview_folder.uid)
            )
            items = self._build_preview_tree(
                classroom_uid=str(classroom.uid),
                root_folder=preview_folder,
                root_docs=root_docs,
            )
        else:
            folder_payload = None
            items = []

        classroom_payload = ClassroomResponseSerializer(classroom).data
        is_favorited = False
        favorite_count = 0
        if consumer_id is not None:
            fav_service = ClassroomFavoriteService()
            is_favorited = fav_service.is_favorited(consumer_id, classroom.uid)
            favorite_count = fav_service.favorite_count(classroom.uid)
            classroom_payload['is_favorited'] = is_favorited
            classroom_payload['favorite_count'] = favorite_count
        else:
            classroom_payload['is_favorited'] = False
            classroom_payload['favorite_count'] = 0

        return {
            'classroom': classroom_payload,
            'preview': {
                'folder': folder_payload,
                'items': items,
            },
            'actions': {
                'type': action_type,
                'requires_payment': action_type == 'checkout',
                'membership_status': membership_status,
                'pay_url': pay_url,
                'amount': amount,
            },
            'is_favorited': is_favorited,
            'favorite_count': favorite_count,
        }

    def _build_preview_tree(self, classroom_uid, root_folder, root_docs):
        """Walk all descendant folders of `root_folder` and return a flat list
        of items, ordered for nested rendering. Each item is one of:

            {"type": "folder", "uid": "...", "name": "...",
             "parent_folder_id": "..." | null, "depth": 0}
            {"type": "doc", "uid": "...", "name": "...", "url": "...",
             "file_type": "...", "size": ..., "folder_id": "...",
             "depth": 0}

        BFS so siblings at the same depth come together; docs appear
        immediately after their parent folder at the same depth.
        """
        from features.resource.repositories.resource_folder_repository import ResourceFolderRepository
        from features.resource.repositories.resource_repository import ResourceRepository
        from features.resource.serializers.resource_folder_serializer import ResourceFolderResponseSerializer
        from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer

        folder_repo = ResourceFolderRepository()
        resource_repo = ResourceRepository()

        items = []
        queue = [(root_folder, 0)]
        while queue:
            current_folder, depth = queue.pop(0)
            items.append({
                'type': 'folder',
                'uid': str(current_folder.uid),
                'name': current_folder.name,
                'parent_folder_id': str(current_folder.parent_folder_id) if current_folder.parent_folder_id else None,
                'is_preview_only': bool(getattr(current_folder, 'is_preview_only', False)),
                'depth': depth,
            })
            folder_docs = resource_repo.get_by_owner_and_folder(
                current_folder.classroom_id, current_folder.uid
            )
            for doc in folder_docs:
                items.append({
                    'type': 'doc',
                    'uid': str(doc.uid),
                    'name': doc.name,
                    'url': doc.url,
                    'file_type': doc.file_type or '',
                    'size': int(getattr(doc, 'size', 0) or 0),
                    'folder_id': str(current_folder.uid),
                    'depth': depth,
                })
            children = folder_repo.get_children(current_folder.classroom_id, current_folder.uid)
            for child in children:
                queue.append((child, depth + 1))
        return items
