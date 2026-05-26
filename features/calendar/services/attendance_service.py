from datetime import datetime, date
from core.services.base_service import BaseService
from features.calendar.repositories.attendance_repository import AttendanceRepository

class AttendanceService(BaseService):
    def __init__(self):
        self.repository = AttendanceRepository()

    def mark_attendance(self, event_id, user_id, status='present', joined_at=None, left_at=None):
        attendance = self.repository.find(event_id, user_id)
        
        data = {
            'status': status,
            'date': date.today()
        }
        
        if joined_at:
            data['joined_at'] = joined_at
        if left_at:
            data['left_at'] = left_at
            
        if attendance:
            return self.update(attendance, **data)
        
        return self.create(
            event_id=event_id,
            user_id=user_id,
            **data
        )

    def audit_daily_attendance(self, user_id, events):
        """
        Check if user attended all events today. 
        If not record exists, mark as absent.
        """
        today = date.today()
        for event in events:
            attendance = self.repository.find(event.uid, user_id)
            if not attendance:
                self.create(
                    event_id=event.uid,
                    user_id=user_id,
                    status='absent',
                    date=today
                )

    def get_user_attendance(self, user_id, date_obj=None):
        if date_obj:
            return self.repository.get_daily_attendance(user_id, date_obj)
        return self.repository.filter(user_id=user_id)
