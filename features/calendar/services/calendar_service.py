from datetime import datetime
from typing import Optional

from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

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
        self._check_overlap(classroom_id, owner_id, kwargs['start_time'], kwargs['end_time'])
        return self.create(space_id=space_id, owner_id=owner_id, classroom_id=classroom_id, **kwargs)

    def update_event(self, event, requester_id, **kwargs):
        self._ensure_event_ownership(event, requester_id)
        if 'classroom_id' in kwargs and kwargs['classroom_id'] != event.classroom_id:
            self._ensure_classroom_ownership(kwargs['classroom_id'], requester_id)
        classroom_id = kwargs.get('classroom_id', event.classroom_id)
        start_time = kwargs.get('start_time', event.start_time)
        end_time = kwargs.get('end_time', event.end_time)
        self._check_overlap(classroom_id, event.owner_id, start_time, end_time, exclude_uid=event.uid)
        return self.update(event, **kwargs)

    def _check_overlap(self, classroom_id, owner_id, start_time, end_time, exclude_uid=None):
        candidates = self.repository.get_by_classroom(classroom_id) if classroom_id else self.repository.get_by_owner(owner_id)
        for candidate in candidates:
            if exclude_uid and str(candidate.uid) == str(exclude_uid):
                continue
            if candidate.start_time < end_time and candidate.end_time > start_time:
                raise ValidationError({'start_time': 'Đã tồn tại lịch trùng ngày/giờ.'})

    def create_recurring_events(self, space_id, owner_id, classroom_id, event_type, title, description, slots):
        self._ensure_classroom_ownership(classroom_id, owner_id)

        existing = list(self.repository.get_by_classroom(classroom_id) if classroom_id else self.repository.get_by_owner(owner_id))
        conflicts = []
        accepted = []
        for slot in slots:
            start_time, end_time = slot['start_time'], slot['end_time']
            if any(e.start_time < end_time and e.end_time > start_time for e in existing):
                conflicts.append({'start_time': start_time, 'end_time': end_time, 'reason': 'Đã tồn tại lịch trùng ngày/giờ.'})
            else:
                accepted.append(slot)

        if conflicts:
            return [], conflicts

        created = [
            self.create(
                space_id=space_id,
                owner_id=owner_id,
                classroom_id=classroom_id,
                type=event_type,
                title=title,
                description=description,
                start_time=slot['start_time'],
                end_time=slot['end_time'],
            )
            for slot in slots
        ]
        return created, []

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
