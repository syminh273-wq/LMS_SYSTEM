import logging
from datetime import datetime
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .base_consumer import BaseWebSocketConsumer

logger = logging.getLogger(__name__)

class AttendanceConsumer(BaseWebSocketConsumer):
    """
    Consumer to handle auto-attendance when user is online.
    """

    async def connect(self):
        self.user = self.scope.get('user', AnonymousUser())

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        await self.accept()
        await self._mark_present()

    async def disconnect(self, close_code):
        await self._mark_left()

    @database_sync_to_async
    def _mark_present(self):
        try:
            from features.calendar.services.attendance_service import AttendanceService
            from features.calendar.services.calendar_service import CalendarService
            from features.account.consumer.models.consumer import Consumer
            
            if not isinstance(self.user, Consumer):
                return

            # Find events happening NOW for this student
            # We'd need to know which classrooms they are in.
            from features.course.classroom.services.classroom_member_service import ClassroomMemberService
            classroom_uids = ClassroomMemberService().get_joined_classroom_uids(self.user.uid)
            
            calendar_service = CalendarService()
            attendance_service = AttendanceService()
            now = datetime.now()
            
            for classroom_id in classroom_uids:
                # This is a bit heavy, in production we might use a better query or cache
                events = calendar_service.get_events(space_id=None, classroom_id=classroom_id)
                for event in events:
                    if event.start_time <= now <= event.end_time:
                        attendance_service.mark_attendance(
                            event_id=event.uid,
                            user_id=self.user.uid,
                            status='present',
                            joined_at=now
                        )
        except Exception as e:
            logger.error(f"Auto-attendance connect error: {e}")

    @database_sync_to_async
    def _mark_left(self):
        try:
            from features.calendar.services.attendance_service import AttendanceService
            from features.calendar.services.calendar_service import CalendarService
            from features.account.consumer.models.consumer import Consumer
            
            if not isinstance(self.user, Consumer):
                return

            classroom_uids = ClassroomMemberService().get_joined_classroom_uids(self.user.uid)
            
            calendar_service = CalendarService()
            attendance_service = AttendanceService()
            now = datetime.now()
            
            for classroom_id in classroom_uids:
                events = calendar_service.get_events(space_id=None, classroom_id=classroom_id)
                for event in events:
                    if event.start_time <= now <= event.end_time:
                        attendance_service.mark_attendance(
                            event_id=event.uid,
                            user_id=self.user.uid,
                            # Keep status as present, just update left_at
                            left_at=now
                        )
        except Exception as e:
            logger.error(f"Auto-attendance disconnect error: {e}")
