from datetime import datetime
from features.course.meeting_room.repositories.meeting_room_participant_repository import MeetingRoomParticipantRepository
from features.course.meeting_room.repositories.meeting_room_repository import MeetingRoomRepository


class MeetingRoomParticipantService:
    def __init__(self):
        self.repo = MeetingRoomParticipantRepository()
        self.room_repo = MeetingRoomRepository()

    def join(self, room_uid, user, role='participant'):
        participant_type = 'space' if hasattr(user, 'logo_url') else 'consumer'
        participant_name = getattr(user, 'full_name', '') or getattr(user, 'username', '') or ''
        participant_avatar = getattr(user, 'avatar_url', '') or getattr(user, 'logo_url', '') or ''

        existing = self.repo.get_participant(room_uid, user.uid)
        if existing and not existing.is_deleted:
            return existing

        participant = self.repo.create(
            room_uid=room_uid,
            participant_id=user.uid,
            participant_type=participant_type,
            participant_name=participant_name,
            participant_avatar=participant_avatar,
            role=role,
            joined_at=datetime.utcnow(),
        )

        # Increment participant_count on the room
        try:
            room = self.room_repo.find(room_uid)
            self.room_repo.update(room, participant_count=room.participant_count + 1)
        except Exception:
            pass

        return participant

    def leave(self, room_uid, participant_id):
        existing = self.repo.get_participant(room_uid, participant_id)
        if existing and not existing.is_deleted:
            existing.update(is_deleted=True, left_at=datetime.utcnow())

            # Decrement participant_count on the room
            try:
                room = self.room_repo.find(room_uid)
                count = max(0, room.participant_count - 1)
                self.room_repo.update(room, participant_count=count)
            except Exception:
                pass

    def get_participants(self, room_uid):
        return list(self.repo.get_by_room(room_uid))

    def is_participant(self, room_uid, participant_id):
        p = self.repo.get_participant(room_uid, participant_id)
        return p is not None and not p.is_deleted
