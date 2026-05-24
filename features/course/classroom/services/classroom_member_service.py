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
        return member

    def approve(self, classroom_uid, member_id, approved_by_id):
        from features.course.classroom.services.classroom_service import Service
        from rest_framework.exceptions import PermissionDenied, NotFound
        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(approved_by_id):
            raise PermissionDenied("Chỉ giáo viên mới có thể duyệt thành viên.")
        member = self.repo.approve_member(classroom_uid, member_id)
        if not member:
            raise NotFound("Không tìm thấy thành viên.")
        return member

    def reject(self, classroom_uid, member_id, rejected_by_id):
        from features.course.classroom.services.classroom_service import Service
        from rest_framework.exceptions import PermissionDenied
        classroom = Service().find(str(classroom_uid))
        if str(classroom.teacher_id) != str(rejected_by_id):
            raise PermissionDenied("Chỉ giáo viên mới có thể từ chối thành viên.")
        self.leave(classroom_uid, member_id)

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
