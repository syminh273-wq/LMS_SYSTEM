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

        result = None
        if attendance:
            result = self.update(attendance, **data)
        else:
            result = self.create(
                event_id=event_id,
                user_id=user_id,
                **data
            )

        try:
            from uuid import UUID
            from features.ranking.services.xp_service import XPService
            if str(status).lower() == 'present':
                XPService().award(
                    student_id=user_id,
                    event_type='attendance_present',
                    ref_type='attendance',
                    ref_id=UUID(str(event_id)),
                    description='Có mặt tại buổi học',
                    count_field='attendance_count',
                )
        except Exception:
            pass

        return result

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
