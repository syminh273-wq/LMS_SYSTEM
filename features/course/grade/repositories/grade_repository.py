from datetime import datetime
from uuid import UUID

from features.course.grade.models import Grade


class GradeRepository:
    def create(self, **data):
        return Grade.create(**data)

    def get_by_uid(self, uid):
        try:
            grade_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except ValueError:
            return None

        return Grade.objects(bucket=0, uid=grade_uid, is_deleted=False).first()

    def list_by_submission(self, submission_id):
        return Grade.objects(submission_id=submission_id, is_deleted=False)

    def update(self, grade, **data):
        for key, value in data.items():
            setattr(grade, key, value)
        grade.save()
        return grade

    def soft_delete_by_submission(self, submission_id):
        for grade in self.list_by_submission(submission_id):
            grade.is_deleted = True
            grade.deleted_at = datetime.utcnow()
            grade.save()
