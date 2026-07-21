from core.repositories.base_repository import BaseRepository
from features.course.classroom.models import Classroom

class Repository(BaseRepository):
    model = Classroom

    def get_active_classrooms(self):
        # We must filter by bucket to use ORDER BY uid in Cassandra
        return self.filter(bucket=0, status='active', is_deleted=False).order_by('uid')

    def get_by_teacher(self, teacher_id):
        # Global filter without order_by will work fine
        return self.filter(teacher_id=teacher_id, is_deleted=False)

    def discover(self, category=None, pricing_type=None, visibility_type='public', search=None):
        """List public classrooms for the consumer Discover page.

        Cassandra does not allow `ORDER BY` when a query relies on a
        secondary index, so we filter with the indexed columns only and
        sort / substring-search in Python.
        """
        qs = self.filter(
            status='active',
            visibility_type=visibility_type,
            is_deleted=False,
        )
        if category:
            qs = qs.filter(category=category)
        if pricing_type:
            qs = qs.filter(pricing_type=pricing_type)
        items = list(qs)
        if search:
            needle = search.lower()
            items = [
                c for c in items
                if needle in (c.name or '').lower()
                or needle in (c.description or '').lower()
            ]
        items.sort(key=lambda c: c.uid, reverse=True)
        return items
