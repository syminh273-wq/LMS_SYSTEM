from core.repositories.base_repository import BaseRepository
from features.calendar.models.attendance import Attendance

class AttendanceRepository(BaseRepository):
    model = Attendance

    def get_by_event(self, event_id):
        return self.filter(event_id=event_id)

    def get_user_attendance_for_event(self, event_id, user_id):
        return self.filter(event_id=event_id, user_id=user_id).first()

    def get_daily_attendance(self, user_id, date):
        return self.filter(user_id=user_id, date=date)
    
    def find(self, event_id, user_id):
        return self.filter(event_id=event_id, user_id=user_id).first()

    def count_present_by_user_events(self, user_id, event_ids):
        """Count how many events in `event_ids` the user attended (status='present')."""
        if not event_ids:
            return 0
        return self.filter(user_id=user_id, status='present', event_id__in=list(event_ids)).count()
