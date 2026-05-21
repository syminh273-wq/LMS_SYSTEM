from datetime import datetime
from core.notification.dto.notification_dto import NotificationPayloadDto
from features.course.meeting_room.repositories.meeting_room_repository import MeetingRoomRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from core.notification.services.notification_service import NotificationService
from core.notification.enums.notification_provider import NotificationProvider

VALID_STATUSES = ('waiting', 'active', 'ended')


class MeetingRoomService:
    def __init__(self):
        self.repo = MeetingRoomRepository()
        self.member_repo = ClassroomMemberRepository()
        self.notification_service = NotificationService(NotificationProvider.REALTIME_DB.value)
        self.fcm_service = NotificationService(NotificationProvider.FCM.value)

    def create(self, host, data: dict):
        from features.account.space.models.space import Space
        from features.account.consumer.models.consumer import Consumer

        if isinstance(host, Space):
            host_type = 'space'
            host_name = host.full_name or host.name or host.email or 'Space'
        elif isinstance(host, Consumer):
            host_type = 'consumer'
            host_name = host.full_name or host.username or host.email or 'Consumer'
        else:
            host_type = 'unknown'
            host_name = 'Unknown'

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

    def quick_start(self, host, data: dict):
        """Create and start a meeting in one go."""
        room = self.create(host, data)
        return self.update_status(room, 'active')

    def update_status(self, room, status: str):
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}.")

        kwargs = {'status': status}
        if status == 'active' and not room.started_at:
            kwargs['started_at'] = datetime.utcnow()
            # Notify members if linked to a classroom
            if room.classroom_uid:
                self._notify_meeting_started(room)
        elif status == 'ended':
            kwargs['ended_at'] = datetime.utcnow()

        return self.repo.update(room, **kwargs)

    def _notify_meeting_started(self, room):
        """Notify all members of the classroom about the meeting."""
        members = self.member_repo.get_members(room.classroom_uid)
        
        # 1. Realtime DB notification (existing)
        payload = {
            'type': 'meeting_started',
            'room_uid': str(room.uid),
            'classroom_uid': str(room.classroom_uid),
            'title': room.title,
            'host_name': room.host_name,
            'started_at': datetime.utcnow().isoformat()
        }
        
        for member in members:
            channel = f"notifications/{member.member_id}"
            self.notification_service.push_message(channel, payload)

        # 2. FCM Push Notification (via topic)
        topic = f"classroom_{str(room.classroom_uid)}"
        fcm_payload = NotificationPayloadDto(
            event="MEETING",
            action="STARTED",
            sub_action="NEW_MEETING",
            trigger={
                "room_uid": str(room.uid),
                "classroom_uid": str(room.classroom_uid),
                "host_name": room.host_name
            },
            title=f"Meeting started: {room.title}",
            body=f"{room.host_name} has started a meeting in your classroom."
        )
        self.fcm_service.send_notification(topic, fcm_payload, mode="topic")

    def update(self, room, **kwargs):
        # Prevent direct status changes through generic update; use update_status instead
        kwargs.pop('status', None)
        return self.repo.update(room, **kwargs)

    def delete(self, room):
        self.repo.delete(room)
