import logging
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository

logger = logging.getLogger(__name__)


class ClassroomMemberService:
    def __init__(self):
        self.repo = ClassroomMemberRepository()

    def join(self, classroom_uid, user, role='student'):
        existing = self.repo.get_member(classroom_uid, user.uid)
        if existing and not existing.is_deleted:
            return existing
        name = getattr(user, 'full_name', '') or getattr(user, 'username', '') or ''
        avatar = getattr(user, 'avatar_url', '') or getattr(user, 'logo_url', '') or ''
        member_type = 'space' if hasattr(user, 'logo_url') else 'consumer'

        member = self.repo.create(
            member_id=user.uid,
            classroom_uid=classroom_uid,
            member_type=member_type,
            member_name=name,
            member_avatar=avatar,
            role=role,
            status='pending',
        )
        try:
            self._notify_teacher_pending(classroom_uid, user, name)
        except Exception as e:
            logger.warning(f"[ClassroomMember] Failed to send pending notification: {e}")

        self._push_pending_signal(classroom_uid, name)

        return member

    def mark_paid_pending(self, classroom_uid, consumer_id):
        """Called by payment IPN after a successful MoMo transaction.

        Marks `has_paid=True` and keeps `status='pending'` so the teacher
        still has to approve. The student sees a 'Đã thanh toán · Chờ duyệt'
        state in the UI until approval.
        """
        from features.course.classroom.services.classroom_service import Service
        from features.account.consumer.repositories import ConsumerRepository
        from datetime import datetime

        classroom = Service().find(str(classroom_uid))
        consumer = ConsumerRepository().find(consumer_id)
        if not consumer:
            logger.warning(f"[ClassroomMember] mark_paid_pending: consumer {consumer_id} not found")
            return None

        existing = self.repo.get_member(classroom_uid, consumer_id)
        if existing and not existing.is_deleted:
            self.repo.update(existing, has_paid=True, paid_at=datetime.utcnow())
            member = existing
        else:
            name = getattr(consumer, 'full_name', '') or getattr(consumer, 'username', '') or ''
            avatar = getattr(consumer, 'avatar_url', '') or ''
            member = self.repo.create(
                member_id=consumer.uid,
                classroom_uid=classroom_uid,
                member_type='consumer',
                member_name=name,
                member_avatar=avatar,
                role='student',
                status='pending',
                has_paid=True,
                paid_at=datetime.utcnow(),
            )

        try:
            self._notify_teacher_pending(classroom_uid, consumer, member.member_name)
        except Exception as exc:
            logger.warning(f"[ClassroomMember] Failed to notify teacher after payment: {exc}")
        self._push_pending_signal(classroom_uid, member.member_name)

        try:
            from features.notification.services.notification_service import NotificationService
            NotificationService().send_notification(
                target_uid=consumer_id,
                notify_type='classroom_payment_received',
                title='Thanh toán thành công',
                content=f'Bạn đã thanh toán cho lớp "{classroom.name}". Vui lòng chờ giáo viên duyệt.',
                metadata={
                    'classroom_uid': str(classroom.uid),
                    'classroom_name': classroom.name,
                    'status': 'pending',
                },
            )
        except Exception as exc:
            logger.warning(f"[ClassroomMember] Failed to send payment notification: {exc}")

        return member

    def approve_paid_member(self, classroom_uid, consumer_id):
        """Backward-compatible alias. Always sets status='pending' and
        has_paid=True. Teacher must still call `approve` to finalize."""
        return self.mark_paid_pending(classroom_uid, consumer_id)

    def _register_teacher_contact(self, classroom, consumer_id, name, avatar):
        from features.course.classroom.repositories.teacher_contact_repository import TeacherContactRepository
        from features.account.consumer.repositories import ConsumerRepository
        from core.search_engine.typesense.indexer import LMSIndexer
        consumer = ConsumerRepository().find(consumer_id)
        contact = TeacherContactRepository().register(
            teacher_id=classroom.teacher_id,
            consumer_uid=consumer_id,
            consumer_name=name,
            consumer_email=getattr(consumer, 'email', ''),
            consumer_avatar=avatar or '',
            first_name=getattr(consumer, 'first_name', '') or '',
            last_name=getattr(consumer, 'last_name', '') or '',
        )
        if contact:
            LMSIndexer.index_teacher_contact(contact)

    def approve(self, classroom_uid, member_id, approved_by_id):
        from features.course.classroom.services.classroom_service import Service
        from features.course.classroom.repositories.teacher_contact_repository import TeacherContactRepository
        from features.account.consumer.repositories import ConsumerRepository
        from rest_framework.exceptions import PermissionDenied, NotFound

        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(approved_by_id):
            raise PermissionDenied("Chỉ giáo viên mới có thể duyệt thành viên.")
        member = self.repo.approve_member(classroom_uid, member_id)
        if not member:
            raise NotFound("Không tìm thấy thành viên.")

        # Register student in teacher's contact list + index to Typesense (idempotent)
        try:
            from core.search_engine.typesense.indexer import LMSIndexer
            consumer = ConsumerRepository().find(member_id)
            contact = TeacherContactRepository().register(
                teacher_id=classroom.teacher_id,
                consumer_uid=member_id,
                consumer_name=member.member_name,
                consumer_email=getattr(consumer, 'email', ''),
                consumer_avatar=member.member_avatar or '',
                first_name=getattr(consumer, 'first_name', '') or '',
                last_name=getattr(consumer, 'last_name', '') or '',
            )
            if contact:
                LMSIndexer.index_teacher_contact(contact)
        except Exception:
            pass  # never block the approval flow

        # Realtime Firebase event → student frontend
        self._push_membership_event(member_id, classroom_uid, classroom.name, 'approved')

        # Persistent notification for student (bell icon + history)
        try:
            from features.notification.services.notification_service import NotificationService
            NotificationService().send_notification(
                target_uid=member_id,
                notify_type='classroom_approved',
                title='Yêu cầu được chấp nhận',
                content=f'Bạn đã được duyệt vào lớp "{classroom.name}"',
                metadata={
                    'classroom_uid': str(classroom.uid),
                    'classroom_name': classroom.name,
                    'status': 'approved',
                },
            )
        except Exception as e:
            logger.warning(f"[ClassroomMember] Failed to send approval notification: {e}")

        return member

    def reject(self, classroom_uid, member_id, rejected_by_id):
        from features.course.classroom.services.classroom_service import Service
        from rest_framework.exceptions import PermissionDenied
        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(rejected_by_id):
            raise PermissionDenied("Chỉ giáo viên mới có thể từ chối thành viên.")
        self.leave(classroom_uid, member_id)
        self._push_membership_event(member_id, classroom_uid, classroom.name, 'rejected')

        try:
            from features.notification.services.notification_service import NotificationService
            NotificationService().send_notification(
                target_uid=member_id,
                notify_type='classroom_rejected',
                title='Yêu cầu bị từ chối',
                content=f'Yêu cầu tham gia lớp "{classroom.name}" đã bị từ chối',
                metadata={
                    'classroom_uid': str(classroom.uid),
                    'classroom_name': classroom.name,
                    'status': 'rejected',
                },
            )
        except Exception as e:
            logger.warning(f"[ClassroomMember] Failed to send rejection notification: {e}")

    def get_pending_members(self, classroom_uid):
        return list(self.repo.get_pending_members(classroom_uid))

    def _notify_teacher_pending(self, classroom_uid, user, student_name):
        from features.course.classroom.services.classroom_service import Service
        from features.notification.services.notification_service import NotificationService
        classroom = Service().find(str(classroom_uid))
        if not classroom or not classroom.teacher_id:
            return
        NotificationService().send_notification(
            target_uid=classroom.teacher_id,
            notify_type='student_join_request',
            title='Yêu cầu tham gia lớp học',
            content=f'{student_name} đang chờ được phê duyệt vào lớp {classroom.name}',
            metadata={
                'classroom_uid': str(classroom.uid),
                'classroom_name': classroom.name,
                'student_uid': str(user.uid),
                'student_name': student_name,
            }
        )

    def leave(self, classroom_uid, member_id):
        m = self.repo.get_member(classroom_uid, member_id)
        if m:
            m.update(is_deleted=True)

    def get_members(self, classroom_uid):
        return list(self.repo.get_members(classroom_uid))

    def is_member(self, classroom_uid, member_id):
        return self.repo.is_member(classroom_uid, member_id)

    def kick(self, classroom_uid, member_id, kicked_by_id):
        from features.course.classroom.services.classroom_service import Service
        from rest_framework.exceptions import PermissionDenied
        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(kicked_by_id):
            raise PermissionDenied("Chỉ giáo viên mới có thể kick sinh viên.")
        self.leave(classroom_uid, member_id)

    def get_joined_classroom_uids(self, member_id):
        rows = self.repo.get_by_member(member_id)
        return [r.classroom_uid for r in rows]

    def _push_pending_signal(self, classroom_uid, student_name):
        """Overwrite a single Firebase node so teacher's UI listener fires and refetches."""
        from datetime import datetime
        from core.firebase.client.firebase_app import FirebaseApp
        try:
            FirebaseApp.set_value(
                f"pending_requests/{classroom_uid}",
                {"at": datetime.utcnow().isoformat(), "student_name": student_name},
            )
        except Exception:
            pass

    def _push_membership_event(self, consumer_uid, classroom_uid, classroom_name, status):
        """Write a realtime event to Firebase so the student's frontend reacts immediately."""
        from datetime import datetime
        from core.firebase.client.firebase_app import FirebaseApp
        try:
            FirebaseApp.set_value(
                f"membership_events/{consumer_uid}/{classroom_uid}",
                {
                    "status": status,
                    "classroom_uid": str(classroom_uid),
                    "classroom_name": classroom_name,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
        except Exception:
            pass
