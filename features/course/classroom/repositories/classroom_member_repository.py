from core.repositories.base_repository import BaseRepository
from features.course.classroom.models.classroom_member import ClassroomMember


class ClassroomMemberRepository(BaseRepository):
    model = ClassroomMember

    def get_members(self, classroom_uid):
        return self.model.objects.filter(classroom_uid=classroom_uid, is_deleted=False)

    def get_member(self, classroom_uid, member_id):
        return self.model.objects.filter(
            classroom_uid=classroom_uid, member_id=member_id
        ).first()

    def is_member(self, classroom_uid, member_id):
        m = self.get_member(classroom_uid, member_id)
        return m is not None and not m.is_deleted
