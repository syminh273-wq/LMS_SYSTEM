from core.repositories.base_repository import BaseRepository
from features.course.meeting_room.models.meeting_room import MeetingRoom


class MeetingRoomRepository(BaseRepository):
    model = MeetingRoom

    def get_by_host(self, host_id):
        return self.model.objects.filter(host_id=host_id, is_deleted=False)

    def get_by_classroom(self, classroom_uid):
        return self.model.objects.filter(classroom_uid=classroom_uid, is_deleted=False)

    def get_active_rooms(self):
        return self.model.objects.filter(bucket=0, status='active', is_deleted=False)
