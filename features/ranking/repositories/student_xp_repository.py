from core.repositories.base_repository import BaseRepository
from features.ranking.models.student_xp import StudentXP


class StudentXPRepository(BaseRepository):
    model = StudentXP

    def get(self, student_id):
        return self.model.objects(student_id=student_id).first()

    def get_or_create(self, student_id):
        existing = self.get(student_id)
        if existing:
            return existing, False
        created = self.model.create(student_id=student_id)
        return created, True

    def get_top(self, limit=10):
        """Return top-N students by total_xp. Cassandra clustering cannot
        order by a non-key column, so we pull all rows and sort in Python.
        For very large user bases this would need a denormalized leaderboard
        table — out of scope for now (use a 1k–10k cap in production)."""
        rows = list(self.model.objects.all().limit(1000))
        rows = [r for r in rows if r is not None]
        rows.sort(key=lambda r: (-(r.total_xp or 0), r.student_id))
        return rows[: max(1, int(limit))]

    def update_counters(self, student_xp, **fields):
        from datetime import datetime
        for k, v in fields.items():
            setattr(student_xp, k, v)
        student_xp.updated_at = datetime.utcnow()
        student_xp.save()
        return student_xp
