from datetime import datetime
from features.course.classroom.models.teacher_contact import TeacherContact


class TeacherContactRepository:

    def get_by_teacher(self, teacher_id):
        """All students who ever studied with this teacher."""
        return list(TeacherContact.objects.filter(teacher_id=teacher_id))

    def get_contact(self, teacher_id, consumer_uid):
        """Direct PK lookup — O(1)."""
        return TeacherContact.objects.filter(
            teacher_id=teacher_id, consumer_uid=consumer_uid
        ).first()

    def exists(self, teacher_id, consumer_uid) -> bool:
        return self.get_contact(teacher_id, consumer_uid) is not None

    def register(self, teacher_id, consumer_uid, consumer_name='',
                 consumer_email='', consumer_avatar='',
                 first_name='', last_name=''):
        """Upsert — returns the TeacherContact instance (existing or newly created)."""
        existing = self.get_contact(teacher_id, consumer_uid)
        if existing:
            return existing
        return TeacherContact.objects.create(
            teacher_id=teacher_id,
            consumer_uid=consumer_uid,
            consumer_name=consumer_name,
            first_name=first_name,
            last_name=last_name,
            consumer_email=consumer_email,
            consumer_avatar=consumer_avatar,
            first_joined_at=datetime.utcnow(),
        )
