from core.repositories.base_repository import BaseRepository
from features.course.classroom.models.classroom_member import ClassroomMember


class ClassroomMemberRepository(BaseRepository):
    model = ClassroomMember

    def get_by_member(self, member_id):
        """All classroom memberships for a user (partition key lookup — fast)."""
        return self.model.objects.filter(member_id=member_id, is_deleted=False)

    def get_members(self, classroom_uid):
        """All members of a classroom (secondary index on classroom_uid)."""
        return self.model.objects.filter(classroom_uid=classroom_uid, is_deleted=False)

    def get_member(self, classroom_uid, member_id):
        return self.model.objects.filter(
            member_id=member_id, classroom_uid=classroom_uid
        ).first()

    def is_member(self, classroom_uid, member_id):
        m = self.get_member(classroom_uid, member_id)
        return m is not None and not m.is_deleted
