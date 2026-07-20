from core.repositories.base_repository import BaseRepository
from features.calendar.models.calendar_event import CalendarEvent


class CalendarEventRepository(BaseRepository):
    model = CalendarEvent

    def get_by_space(self, space_id, type_=None):
        kwargs = {'space_id': space_id, 'is_deleted': False}
        if type_:
            kwargs['type'] = type_
        return self.filter(**kwargs)

    def get_by_classroom(self, classroom_id, type_=None):
        kwargs = {'classroom_id': classroom_id, 'is_deleted': False}
        if type_:
            kwargs['type'] = type_
        return self.filter(**kwargs)

    def get_by_classroom_uids(self, classroom_uids, type_=None):
        results = []
        for cid in classroom_uids:
            results.extend(list(self.get_by_classroom(cid, type_=type_)))
        return results

    def get_events_in_range(self, space_id, start_date, end_date, type_=None):
        kwargs = {
            'space_id': space_id,
            'start_time__gte': start_date,
            'start_time__lte': end_date,
            'is_deleted': False,
        }
        if type_:
            kwargs['type'] = type_
        return self.filter(**kwargs)

    def get_by_classroom_in_range(self, classroom_id, start_date, end_date, type_=None):
        kwargs = {
            'classroom_id': classroom_id,
            'start_time__gte': start_date,
            'start_time__lte': end_date,
            'is_deleted': False,
        }
        if type_:
            kwargs['type'] = type_
        return self.filter(**kwargs)

    def get_by_classroom_uids_in_range(self, classroom_uids, start_date, end_date, type_=None):
        results = []
        for cid in classroom_uids:
            results.extend(list(self.get_by_classroom_in_range(cid, start_date, end_date, type_=type_)))
        return results
