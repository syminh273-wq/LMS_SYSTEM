from core.repositories.base_repository import BaseRepository
from features.course.meeting_room.models.meeting_room_participant import MeetingRoomParticipant


class MeetingRoomParticipantRepository(BaseRepository):
    model = MeetingRoomParticipant

    def get_by_room(self, room_uid):
        return self.model.objects.filter(room_uid=room_uid, is_deleted=False)

    def get_participant(self, room_uid, participant_id):
        return self.model.objects.filter(
            room_uid=room_uid, participant_id=participant_id
        ).first()
