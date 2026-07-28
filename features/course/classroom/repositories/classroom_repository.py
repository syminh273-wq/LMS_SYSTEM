from core.repositories.base_repository import BaseRepository
from core.utils.pid import generate_unique_pid
from features.course.classroom.models import Classroom

class Repository(BaseRepository):
    model = Classroom

    def create(self, **kwargs):
        if not kwargs.get('pid'):
            kwargs['pid'] = generate_unique_pid(self.get_by_pid)
        return super().create(**kwargs)

    def get_active_classrooms(self):
        return sorted(
            list(self.filter(status='active', is_deleted=False)),
            key=lambda c: c.uid,
            reverse=True,
        )

    def get_by_teacher(self, teacher_id):
        return self.filter(teacher_id=teacher_id, is_deleted=False)

    def get_by_pid(self, pid):
        return self.filter(pid=pid, is_deleted=False).first()

    def discover(self, category=None, pricing_type=None, visibility_type='public', search=None):
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
