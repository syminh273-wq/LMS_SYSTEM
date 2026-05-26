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
