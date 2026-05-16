from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository


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
        return self.repo.create(
            member_id=user.uid,
            classroom_uid=classroom_uid,
            member_type=member_type,
            member_name=name,
            member_avatar=avatar,
            role=role,
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
