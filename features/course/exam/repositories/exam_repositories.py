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

    def list_by_teacher(self, teacher_id, status=None, exam_mode=None):
        qs = list(Exam.objects(teacher_id=teacher_id, is_deleted=False))
        if status:
            statuses = status if isinstance(status, list) else [status]
            qs = [e for e in qs if e.status in statuses]
        if exam_mode:
            qs = [e for e in qs if e.exam_mode == exam_mode]
        return qs

    def list_by_classroom(self, classroom_id, status=None, exam_mode=None):
        qs = list(Exam.objects(classroom_id=classroom_id, is_deleted=False))
        if status:
            statuses = status if isinstance(status, list) else [status]
            qs = [e for e in qs if e.status in statuses]
        if exam_mode:
            qs = [e for e in qs if e.exam_mode == exam_mode]
        return qs

    def list_published_by_classroom(self, classroom_id):
        # published = có thể nộp bài; ongoing = đang thi; closed = đã kết thúc
        qs = list(Exam.objects(classroom_id=classroom_id, is_deleted=False))
        return [e for e in qs if e.status in ('published', 'ongoing', 'closed')]

    def update(self, exam, **data):
        for key, value in data.items():
            setattr(exam, key, value)

        exam.save()
        return exam

    def find_by_ref_id_and_classroom(self, ref_id, classroom_id):
        """Return published/ongoing quiz-type exams linked to the given quiz ref_id in a classroom."""
        qs = list(Exam.objects(classroom_id=classroom_id, is_deleted=False))
        return [
            e for e in qs
            if str(getattr(e, "ref_id", "") or "") == str(ref_id)
            and getattr(e, "exam_type", "") == "quiz"
            and e.status in ("published", "ongoing")
        ]

    def soft_delete(self, exam):
        exam.is_deleted = True
        exam.deleted_at = datetime.utcnow()
        exam.save()
        return exam
