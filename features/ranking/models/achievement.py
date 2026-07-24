from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class StudentAchievement(DjangoCassandraModel):
    """Per-student achievement unlock state.

    One row per (student_id, achievement_code). `is_unlocked=True` means
    the achievement was earned; `progress_pct` and `current_value` are
    used for in-progress achievements so the UI can show "3/10".
    """

    student_id = columns.UUID(partition_key=True, required=True)
    achievement_code = columns.Text(primary_key=True, required=True)

    title = columns.Text(default='')
    description = columns.Text(default='')
    icon = columns.Text(default='trophy')
    is_unlocked = columns.Boolean(default=False)

    unlocked_at = columns.DateTime(required=False)

    target_value = columns.Integer(default=0)
    current_value = columns.Integer(default=0)
    progress_pct = columns.Integer(default=0)

    updated_at = columns.DateTime(required=False)

    class Meta:
        get_pk_field = 'achievement_code'

    __table_name__ = 'ranking_achievements'

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    @property
    def pk(self):
        return self.achievement_code

    @property
    def id(self):
        return self.achievement_code
