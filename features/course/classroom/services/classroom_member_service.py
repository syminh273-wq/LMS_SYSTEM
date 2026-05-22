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
        )
        try:
            self._notify_teacher(classroom_uid, user, name)
        except Exception as e:
            logger.warning(f"[ClassroomMember] Failed to send join notification: {e}")
        return member

    def _notify_teacher(self, classroom_uid, user, student_name):
        from features.course.classroom.services.classroom_service import Service
        from features.notification.services.notification_service import NotificationService
        classroom = Service().find(str(classroom_uid))
        if not classroom or not classroom.teacher_id:
            return
        NotificationService().send_notification(
            target_uid=classroom.teacher_id,
            notify_type='student_joined',
            title='Học viên mới tham gia lớp học',
            content=f'{student_name} đã tham gia lớp {classroom.name}',
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

    def get_joined_classroom_uids(self, member_id):
        rows = self.repo.get_by_member(member_id)
        return [r.classroom_uid for r in rows]
