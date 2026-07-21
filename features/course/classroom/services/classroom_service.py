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
        amount = int(classroom.price_vnd or 0)
        if action_type == 'checkout':
            existing_member = member is not None and not member.is_deleted
            if not existing_member:
                try:
                    from features.account.consumer.repositories import ConsumerRepository
                    consumer = ConsumerRepository().find(str(consumer_id))
                    if consumer is not None:
                        from features.course.classroom.services.classroom_member_service import ClassroomMemberService
                        ClassroomMemberService().join(
                            classroom_uid=classroom.uid,
                            user=consumer,
                            role='student',
                        )
                except Exception:
                    pass
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
            docs = ClassroomDocService().list_folder(classroom_uid=str(classroom.uid), folder_id=str(preview_folder.uid))
            folder_payload = ResourceFolderResponseSerializer(preview_folder).data
            docs_payload = ResourceResponseSerializer(docs, many=True).data
        else:
            folder_payload = None
            docs_payload = []

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
                'docs': docs_payload,
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
