from datetime import datetime
from uuid import UUID

from features.course.exam.models import ExamSubmission


class ExamSubmissionRepository:
    def create(self, **data):
        return ExamSubmission.create(**data)

    def get_by_uid(self, uid):
        try:
            submission_uid = uid if isinstance(uid, UUID) else UUID(str(uid))
        except ValueError:
            return None

        return ExamSubmission.objects(bucket=0, uid=submission_uid, is_deleted=False).first()

    def list_by_exam(self, exam_id):
        return ExamSubmission.objects(exam_id=exam_id, is_deleted=False)

    def list_by_student(self, student_id):
        return ExamSubmission.objects(student_id=student_id, is_deleted=False)

    def list_by_exam_and_student(self, exam_id, student_id):
        rows = self.list_by_exam(exam_id)
        return [row for row in rows if str(row.student_id) == str(student_id)]

    def update(self, submission, **data):
        for key, value in data.items():
            setattr(submission, key, value)

        submission.save()
        return submission

    def soft_delete(self, submission):
        submission.is_deleted = True
        submission.deleted_at = datetime.utcnow()
        submission.save()
        return submission
