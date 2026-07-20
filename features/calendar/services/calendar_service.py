from datetime import datetime
from typing import Optional

from rest_framework.exceptions import PermissionDenied, NotFound

from core.services.base_service import BaseService
from features.calendar.repositories.calendar_event_repository import CalendarEventRepository


class CalendarService(BaseService):
    def __init__(self):
        self.repository = CalendarEventRepository()

    def get_events(self, space_id, classroom_id=None, start_date=None, end_date=None):
        if start_date and end_date:
            if classroom_id:
                return self.repository.get_by_classroom_in_range(classroom_id, start_date, end_date)
            return self.repository.get_events_in_range(space_id, start_date, end_date)

        if classroom_id:
            return self.repository.get_by_classroom(classroom_id)

        return self.repository.get_by_space(space_id)

    def get_for_consumer(self, member_id, classroom_id=None, start_date=None, end_date=None, type_=None):
        from features.course.classroom.services.classroom_member_service import ClassroomMemberService

        if classroom_id:
            if not ClassroomMemberService().is_member(classroom_id, member_id):
                raise PermissionDenied("Bạn không phải thành viên của lớp này.")
            if start_date and end_date:
                return self.repository.get_by_classroom_in_range(classroom_id, start_date, end_date, type_=type_)
            return self.repository.get_by_classroom(classroom_id, type_=type_)

        joined_uids = ClassroomMemberService().get_joined_classroom_uids(member_id)
        if not joined_uids:
            return []
        if start_date and end_date:
            return self.repository.get_by_classroom_uids_in_range(joined_uids, start_date, end_date, type_=type_)
        return self.repository.get_by_classroom_uids(joined_uids, type_=type_)

    def create_event(self, space_id, owner_id, classroom_id=None, **kwargs):
        self._ensure_classroom_ownership(classroom_id, owner_id)
        return self.create(space_id=space_id, owner_id=owner_id, classroom_id=classroom_id, **kwargs)

    def update_event(self, event, requester_id, **kwargs):
        self._ensure_event_ownership(event, requester_id)
        if 'classroom_id' in kwargs and kwargs['classroom_id'] != event.classroom_id:
            self._ensure_classroom_ownership(kwargs['classroom_id'], requester_id)
        return self.update(event, **kwargs)

    def delete_event(self, event, requester_id):
        self._ensure_event_ownership(event, requester_id)
        self.delete(event)

    def _ensure_classroom_ownership(self, classroom_id, requester_id):
        if not classroom_id:
            return
        from features.course.classroom.services.classroom_service import Service
        try:
            classroom = Service().find(str(classroom_id))
        except Exception as exc:
            raise NotFound("Lớp học không tồn tại.") from exc
        if str(classroom.teacher_id) != str(requester_id):
            raise PermissionDenied("Bạn không có quyền quản lý lịch của lớp này.")

    def _ensure_event_ownership(self, event, requester_id):
        if str(event.owner_id) != str(requester_id):
            raise PermissionDenied("Bạn không có quyền thao tác trên sự kiện này.")
