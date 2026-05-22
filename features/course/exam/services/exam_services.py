from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from features.course.exam.repositories import ExamRepository


class ExamService:
    MARKDOWN = "markdown"
    FILE_TYPES = ["pdf", "image", "file"]
    STATUSES = ["draft", "published", "closed"]

    def __init__(self):
        self.exam_repo = ExamRepository()

    def validate_content(self, data):
        content_type = data.get("content_type")

        if content_type == self.MARKDOWN:
            if not data.get("content"):
                raise ValueError("content is required when content_type is markdown")
            data["resource_uid"] = None
            return data

        if content_type in self.FILE_TYPES:
            if not data.get("resource_uid"):
                raise ValueError("resource_uid is required when content_type is file/pdf/image")
            data["content"] = ""
            return data

        raise ValueError("Invalid content_type")

    def validate_status(self, status):
        if status not in self.STATUSES:
            raise ValueError("Invalid status")

    def normalize_due_date(self, data):
        if "due_date" not in data:
            return data

        due_date = data.get("due_date")
        if due_date in ("", None):
            data["due_date"] = None
            return data

        if isinstance(due_date, datetime):
            parsed_due_date = due_date
        elif isinstance(due_date, str):
            parsed_due_date = parse_datetime(due_date)
            if parsed_due_date is None:
                parsed_date = parse_date(due_date)
                if parsed_date is None:
                    raise ValueError("Invalid due_date format")
                parsed_due_date = datetime.combine(parsed_date, time.min)
        else:
            raise ValueError("Invalid due_date format")

        if timezone.is_aware(parsed_due_date):
            parsed_due_date = timezone.make_naive(parsed_due_date, timezone.utc)

        data["due_date"] = parsed_due_date
        return data

    def create_exam(self, teacher_id, data):
        data = self.validate_content(data)
        data = self.normalize_due_date(data)
        data["teacher_id"] = teacher_id

        if not data.get("status"):
            data["status"] = "draft"

        self.validate_status(data["status"])

        return self.exam_repo.create(**data)

    def get_exam(self, uid):
        exam = self.exam_repo.get_by_uid(uid)
        if not exam:
            raise ValueError("Exam not found")
        return exam

    def list_teacher_exams(self, teacher_id, classroom_id=None):
        exams = self.exam_repo.list_by_teacher(teacher_id)
        if classroom_id:
            exams = [exam for exam in exams if str(exam.classroom_id) == str(classroom_id)]
        return exams

    def update_exam(self, uid, data):
        exam = self.get_exam(uid)
        data = self.normalize_due_date(data)

        if "content_type" in data:
            data = self.validate_content(data)

        if "status" in data:
            self.validate_status(data["status"])

        return self.exam_repo.update(exam, **data)

    def delete_exam(self, uid):
        exam = self.get_exam(uid)
        return self.exam_repo.soft_delete(exam)

    def list_student_exams(self, classroom_id):
        return self.exam_repo.list_published_by_classroom(classroom_id)
