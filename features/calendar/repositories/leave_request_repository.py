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

    def get_by_classroom(self, classroom_id, student_id=None, status=None):
        kwargs = {'classroom_id': classroom_id, 'is_deleted': False}
        if student_id is not None:
            kwargs['student_id'] = student_id
        if status is not None:
            kwargs['status'] = status
        return list(self.filter(**kwargs))
