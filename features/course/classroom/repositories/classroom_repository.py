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

        We must filter by bucket=0 to satisfy Cassandra's requirement for
        `ORDER BY uid` on a non-primary-key column. Other filters use
        `allow_filtering()` implicitly via the BaseRepository.
        """
        qs = self.filter(
            bucket=0,
            status='active',
            visibility_type=visibility_type,
            is_deleted=False,
        )
        if category:
            qs = qs.filter(category=category)
        if pricing_type:
            qs = qs.filter(pricing_type=pricing_type)
        if search:
            like = f'%{search.lower()}%'
            qs = [c for c in qs if (search.lower() in (c.name or '').lower()) or (search.lower() in (c.description or '').lower())]
        return qs.order_by('uid')
