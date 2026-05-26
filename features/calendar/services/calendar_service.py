from core.services.base_service import BaseService
from features.calendar.repositories.calendar_event_repository import CalendarEventRepository

class CalendarService(BaseService):
    def __init__(self):
        self.repository = CalendarEventRepository()

    def get_events(self, space_id, classroom_id=None, start_date=None, end_date=None):
        if start_date and end_date:
            return self.repository.get_events_in_range(space_id, start_date, end_date)
        
        if classroom_id:
            return self.repository.get_by_classroom(classroom_id)
            
        return self.repository.get_by_space(space_id)

    def create_event(self, **kwargs):
        return self.create(**kwargs)
