from datetime import datetime

from rest_framework.exceptions import NotFound, PermissionDenied

from core.services.base_service import BaseService
from features.calendar.repositories.leave_request_repository import LeaveRequestRepository
from features.resource.services.resource_service import ResourceService


class LeaveRequestService(BaseService):
    def __init__(self):
        self.repository = LeaveRequestRepository()
        self.resource_service = ResourceService()
        self.attendance_service = None

    def get_attendance_service(self):
        if not self.attendance_service:
            from features.calendar.services.attendance_service import AttendanceService
            self.attendance_service = AttendanceService()
        return self.attendance_service

    def submit_request(self, student_id, space_id, reason, evidence_file=None, event_id=None,
                       start_date=None, end_date=None, classroom_id=None):
        evidence_url = None
        if evidence_file:
            upload_result = self.resource_service.upload_resource(
                file_obj=evidence_file,
                owner_id=student_id,
                owner_type='student',
                metadata={'type': 'leave_evidence'},
            )
            if upload_result.get('success') and upload_result.get('data'):
                evidence_url = upload_result['data'].url

        resolved_classroom_id = classroom_id
        if not resolved_classroom_id and event_id:
            try:
                from features.calendar.repositories.calendar_event_repository import CalendarEventRepository
                event = CalendarEventRepository().find(event_id)
                resolved_classroom_id = event.classroom_id
            except Exception:
                resolved_classroom_id = None

        return self.create(
            student_id=student_id,
            space_id=space_id,
            classroom_id=resolved_classroom_id,
            reason=reason,
            evidence_url=evidence_url,
            event_id=event_id,
            start_date=start_date,
            end_date=end_date,
            status='pending',
        )

    def list_for_classroom(self, classroom_id, student_id=None, status=None):
        return self.repository.get_by_classroom(classroom_id, student_id=student_id, status=status)

    def process_request(self, request_uid, teacher_id, status, rejection_reason=None):
        if status not in ('approved', 'rejected'):
            raise PermissionDenied('Trạng thái xử lý không hợp lệ.')

        request = self.repository.find(request_uid)
        if str(request.space_id) != str(teacher_id):
            raise PermissionDenied('Bạn không có quyền xử lý đơn này.')

        if request.status != 'pending':
            raise PermissionDenied('Đơn này đã được xử lý trước đó.')

        update_data = {
            'status': status,
            'processed_by': teacher_id,
            'processed_at': datetime.now(),
        }
        if status == 'rejected' and rejection_reason:
            update_data['rejection_reason'] = rejection_reason
        elif status == 'approved':
            update_data['rejection_reason'] = None

        updated_request = self.update(request, **update_data)

        if status == 'approved' and request.event_id:
            self.get_attendance_service().mark_attendance(
                event_id=request.event_id,
                user_id=request.student_id,
                status='excused',
            )

        return updated_request

    def cancel_request(self, request_uid, student_id):
        request = self.repository.find(request_uid)
        if str(request.student_id) != str(student_id):
            raise PermissionDenied('Bạn không có quyền huỷ đơn này.')
        if request.status != 'pending':
            raise PermissionDenied('Chỉ có thể huỷ đơn đang chờ xử lý.')

        return self.update(request, status='cancelled', processed_at=datetime.now())
