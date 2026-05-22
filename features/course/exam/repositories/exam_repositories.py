from datetime import datetime
from uuid import UUID

from features.course.exam.models import Exam


class ExamRepository:
    def create(self, **data):
        return Exam.create(**data)

    def get_by_uid(self, uid):
        try:
            exam_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except ValueError:
            return None

        return Exam.objects(bucket=0, uid=exam_uid, is_deleted=False).first()

    def list_by_teacher(self, teacher_id):
        return Exam.objects(teacher_id=teacher_id, is_deleted=False)

    def list_published_by_classroom(self, classroom_id):
        try:
            classroom_uid = classroom_id if isinstance(classroom_id, UUID) else UUID(str(classroom_id))
        except ValueError:
            return []

        return Exam.objects(
            classroom_id=classroom_uid,
            status="published",
            is_deleted=False
        )

    def update(self, exam, **data):
        for key, value in data.items():
            setattr(exam, key, value)

        exam.save()
        return exam

    def soft_delete(self, exam):
        exam.is_deleted = True
        exam.deleted_at = datetime.utcnow()
        exam.save()
        return exam
