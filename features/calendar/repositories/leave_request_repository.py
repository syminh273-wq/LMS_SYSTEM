from core.repositories.base_repository import BaseRepository
from features.calendar.models.leave_request import LeaveRequest


class LeaveRequestRepository(BaseRepository):
    model = LeaveRequest

    def get_by_student(self, student_id):
        return list(self.filter(student_id=student_id, is_deleted=False))

    def get_by_space(self, space_id):
        return list(self.filter(space_id=space_id, is_deleted=False))

    def get_pending_requests(self, space_id):
        return list(self.filter(space_id=space_id, status='pending', is_deleted=False))

    def get_by_space_student(self, space_id, student_id):
        return list(self.filter(space_id=space_id, student_id=student_id, is_deleted=False))
