from datetime import datetime
from core.services.base_service import BaseService
from features.calendar.repositories.leave_request_repository import LeaveRequestRepository
from features.resource.services.resource_service import ResourceService

class LeaveRequestService(BaseService):
    def __init__(self):
        self.repository = LeaveRequestRepository()
        self.resource_service = ResourceService()
        self.attendance_service = None # Lazy import to avoid circular dependency

    def get_attendance_service(self):
        if not self.attendance_service:
            from features.calendar.services.attendance_service import AttendanceService
            self.attendance_service = AttendanceService()
        return self.attendance_service

    def submit_request(self, student_id, space_id, reason, evidence_file=None, event_id=None, start_date=None, end_date=None):
        evidence_url = None
        if evidence_file:
            upload_result = self.resource_service.upload_resource(
                file_obj=evidence_file,
                owner_id=student_id,
                owner_type='student',
                metadata={'type': 'leave_evidence'}
            )
            if upload_result['success']:
                evidence_url = upload_result['data'].url

        return self.create(
            student_id=student_id,
            space_id=space_id,
            reason=reason,
            evidence_url=evidence_url,
            event_id=event_id,
            start_date=start_date,
            end_date=end_date,
            status='pending'
        )

    def process_request(self, request_uid, teacher_id, status, rejection_reason=None):
        request = self.find(request_uid)
        
        update_data = {
            'status': status,
            'processed_by': teacher_id,
            'processed_at': datetime.now()
        }
        
        if status == 'rejected' and rejection_reason:
            update_data['rejection_reason'] = rejection_reason
            
        updated_request = self.update(request, **update_data)
        
        # If approved, automatically update attendance to 'excused'
        if status == 'approved' and request.event_id:
            self.get_attendance_service().mark_attendance(
                event_id=request.event_id,
                user_id=request.student_id,
                status='excused'
            )
            
        return updated_request
