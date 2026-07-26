from datetime import datetime
from features.course.classroom.models.teacher_contact import TeacherContact


def _u(v):
    from uuid import UUID
    return UUID(str(v)) if not isinstance(v, UUID) else v


class TeacherContactRepository:

    def get_by_teacher(self, teacher_id):
        """All students who ever studied with this teacher."""
        return list(TeacherContact.objects.filter(teacher_id=_u(teacher_id)))

    def get_contact(self, teacher_id, consumer_uid):
        """Direct PK lookup — O(1)."""
        return TeacherContact.objects.filter(
            teacher_id=_u(teacher_id), consumer_uid=_u(consumer_uid)
        ).first()

    def exists(self, teacher_id, consumer_uid) -> bool:
        return self.get_contact(teacher_id, consumer_uid) is not None

    def register(self, teacher_id, consumer_uid, consumer_name='',
                 consumer_email='', consumer_avatar='',
                 first_name='', last_name=''):
        """Upsert on first contact (usually 'joined').  Returns the
        TeacherContact instance (existing or newly created)."""
        existing = self.get_contact(teacher_id, consumer_uid)
        if existing:
            return existing
        now = datetime.utcnow()
        return TeacherContact.objects.create(
            teacher_id=_u(teacher_id),
            consumer_uid=_u(consumer_uid),
            consumer_name=consumer_name,
            first_name=first_name,
            last_name=last_name,
            consumer_email=consumer_email,
            consumer_avatar=consumer_avatar,
            first_joined_at=now,
            last_contact_at=now,
            last_contact_type='joined',
            contact_count=1,
        )

    def record_contact(self, teacher_id, consumer_uid, contact_type,
                       ref_id=None, consumer_name=None,
                       consumer_email=None, consumer_avatar=None,
                       first_name=None, last_name=None):
        """Record a new interaction with an existing or new contact.

        Auto-creates the row on first contact.  Updates denormalized
        last_contact_* + contact_count for cheap list rendering.
        """
        existing = self.get_contact(teacher_id, consumer_uid)
        now = datetime.utcnow()
        if existing:
            existing.last_contact_at = now
            existing.last_contact_type = contact_type
            if ref_id is not None:
                existing.last_contact_ref_id = _u(ref_id)
            existing.contact_count = (existing.contact_count or 0) + 1
            if consumer_name is not None:
                existing.consumer_name = consumer_name
            if consumer_email is not None:
                existing.consumer_email = consumer_email
            if consumer_avatar is not None:
                existing.consumer_avatar = consumer_avatar
            if first_name is not None:
                existing.first_name = first_name
            if last_name is not None:
                existing.last_name = last_name
            existing.save()
            return existing

        return TeacherContact.objects.create(
            teacher_id=_u(teacher_id),
            consumer_uid=_u(consumer_uid),
            consumer_name=consumer_name or '',
            first_name=first_name or '',
            last_name=last_name or '',
            consumer_email=consumer_email or '',
            consumer_avatar=consumer_avatar or '',
            first_joined_at=now,
            last_contact_at=now,
            last_contact_type=contact_type,
            last_contact_ref_id=_u(ref_id) if ref_id is not None else None,
            contact_count=1,
        )
