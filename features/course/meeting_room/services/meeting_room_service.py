from datetime import datetime
from features.course.meeting_room.repositories.meeting_room_repository import MeetingRoomRepository

VALID_STATUSES = ('waiting', 'active', 'ended')


class MeetingRoomService:
    def __init__(self):
        self.repo = MeetingRoomRepository()

    def create(self, host, data: dict):
        host_type = 'space' if hasattr(host, 'logo_url') else 'consumer'
        host_name = getattr(host, 'full_name', '') or getattr(host, 'username', '') or ''
        return self.repo.create(
            host_id=host.uid,
            host_type=host_type,
            host_name=host_name,
            title=data['title'],
            description=data.get('description', ''),
            classroom_uid=data.get('classroom_uid'),
            max_participants=data.get('max_participants', 0),
            status='waiting',
        )

    def find(self, uid):
        return self.repo.find(uid)

    def get_by_host(self, host_id):
        return self.repo.get_by_host(host_id)

    def get_by_classroom(self, classroom_uid):
        return self.repo.get_by_classroom(classroom_uid)

    def update_status(self, room, status: str):
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}.")

        kwargs = {'status': status}
        if status == 'active' and not room.started_at:
            kwargs['started_at'] = datetime.utcnow()
        elif status == 'ended':
            kwargs['ended_at'] = datetime.utcnow()

        return self.repo.update(room, **kwargs)

    def update(self, room, **kwargs):
        # Prevent direct status changes through generic update; use update_status instead
        kwargs.pop('status', None)
        return self.repo.update(room, **kwargs)

    def delete(self, room):
        self.repo.delete(room)
