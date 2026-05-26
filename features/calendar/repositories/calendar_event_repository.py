from core.repositories.base_repository import BaseRepository
from features.calendar.models.calendar_event import CalendarEvent

class CalendarEventRepository(BaseRepository):
    model = CalendarEvent

    def get_by_space(self, space_id):
        return self.filter(space_id=space_id, is_deleted=False)

    def get_by_classroom(self, classroom_id):
        return self.filter(classroom_id=classroom_id, is_deleted=False)
    
    def get_events_in_range(self, space_id, start_date, end_date):
        # Cassandra range query needs ALLOW FILTERING if not using clustering keys properly
        # But we can try to filter by space_id first
        return self.filter(
            space_id=space_id, 
            start_time__gte=start_date, 
            start_time__lte=end_date,
            is_deleted=False
        )
