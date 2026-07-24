from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel

from core.utils.uuid import uuid7


class StudentXP(DjangoCassandraModel):
    """Denormalized XP counter per student. One row per student.

    Read in O(1) for the level/profile screen. Written every time XP is
    awarded (see `XPService.award`).
    """

    student_id = columns.UUID(primary_key=True, required=True)

    total_xp = columns.BigInt(default=0)

    level = columns.Integer(default=1)
    current_level_xp = columns.BigInt(default=0)
    next_level_xp = columns.BigInt(default=100)

    streak_days = columns.Integer(default=0)
    last_active_date = columns.Date(required=False)
    last_active_at = columns.DateTime(required=False)

    classrooms_joined_count = columns.Integer(default=0)
    quizzes_passed_count = columns.Integer(default=0)
    exams_passed_count = columns.Integer(default=0)
    perfect_scores_count = columns.Integer(default=0)
    certificates_count = columns.Integer(default=0)
    attendance_count = columns.Integer(default=0)

    updated_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = 'student_id'

    __table_name__ = 'ranking_student_xps'

    def save(self, *args, **kwargs):
        from datetime import datetime
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    @property
    def pk(self):
        return self.student_id

    @property
    def id(self):
        return self.student_id
