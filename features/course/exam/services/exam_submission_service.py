from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from features.course.classroom.repositories import Repository as ClassroomRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository
from features.resource.repositories import ResourceRepository
from features.resource.services import ResourceService


class ExamSubmissionService:
    MARKDOWN = "markdown"
    FILE_TYPES = ["pdf", "image", "file"]
    STATUSES = ["submitted", "late", "graded", "returned"]

    def __init__(self):
        self.classroom_repo = ClassroomRepository()
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.member_repo = ClassroomMemberRepository()
        self.resource_repo = ResourceRepository()
        self.resource_service = ResourceService()

    def validate_content(self, data, student_id=None):
        content_type = data.get("content_type")
        file_obj = data.pop("file", None)
        metadata = data.pop("metadata", None)

        if content_type == self.MARKDOWN:
            if not data.get("content"):
                raise ValidationError({"content": "content is required when content_type is markdown"})
            data["resource_uid"] = None
            data["resource_url"] = ""
            data["resource_name"] = ""
            return data

        if content_type in self.FILE_TYPES:
            if file_obj:
                upload_result = self.resource_service.upload_resource(
                    file_obj=file_obj,
                    owner_id=student_id,
                    owner_type="consumer",
                    metadata=metadata or {},
                )
                if not upload_result.get("success"):
                    raise ValidationError(upload_result)

                resource = upload_result["data"]
                data["resource_uid"] = resource.uid
                data["resource_url"] = resource.url
                data["resource_name"] = resource.name
                data["content"] = data.get("content") or ""
                return data

            resource_uid = data.get("resource_uid")
            if not resource_uid:
                raise ValidationError({"file": "file or resource_uid is required when content_type is file/pdf/image"})

            try:
                resource = self.resource_repo.find(resource_uid)
            except self.resource_repo.model.DoesNotExist:
                raise NotFound("Resource not found")

            if student_id and str(resource.owner_id) != str(student_id):
                raise PermissionDenied("Resource does not belong to this student")

            data["content"] = ""
            data["resource_url"] = resource.url
            data["resource_name"] = resource.name
            return data

        raise ValidationError({"content_type": "Invalid content_type"})

    def validate_status(self, status):
        if status not in self.STATUSES:
            raise ValueError("Invalid status")

    def get_exam_for_submission(self, exam_id):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise NotFound("Exam not found")
        if exam.status != "published":
            raise ValidationError("Exam is not open for submissions")
        return exam

    def assert_student_membership(self, classroom_id, student_id):
        if not self.member_repo.is_member(classroom_id, student_id):
            raise PermissionDenied("Student is not a member of this classroom")

    def get_classroom_for_submission(self, classroom_id):
        classroom = self.classroom_repo.get_by_uid(classroom_id)
        if not classroom:
            raise NotFound("Classroom not found")
        return classroom

    def get_exam_for_classroom_submission(self, classroom_id, exam_id):
        self.get_classroom_for_submission(classroom_id)
        exam = self.get_exam_for_submission(exam_id)
        if str(exam.classroom_id) != str(classroom_id):
            raise NotFound("Exam not found")
        return exam

    def build_submission_status(self, exam):
        if not exam.due_date:
            return "submitted"

        now = timezone.now()
        due_date = exam.due_date
        if timezone.is_naive(now):
            now = timezone.make_aware(now, datetime_timezone.utc)
        if timezone.is_naive(due_date):
            due_date = timezone.make_aware(due_date, datetime_timezone.utc)

        return "late" if now > due_date else "submitted"

    def submit_exam(self, exam_id, student_id, data):
        exam = self.get_exam_for_submission(exam_id)
        self.assert_student_membership(exam.classroom_id, student_id)
        return self.submit_exam_with_exam(exam, student_id, data)

    def submit_exam_with_exam(self, exam, student_id, data):
        existing = self.submission_repo.list_by_exam_and_student(exam.uid, student_id)

        data = self.validate_content(data, student_id=student_id)
        data["exam_id"] = exam.uid
        data["classroom_id"] = exam.classroom_id
        data["student_id"] = student_id
        data["status"] = self.build_submission_status(exam)
        data["submitted_at"] = datetime.utcnow()

        if existing:
            data["grade"] = None
            data["feedback"] = ""
            data["graded_by"] = None
            data["graded_at"] = None
            return self.submission_repo.update(existing[0], **data), False

        return self.submission_repo.create(**data), True

    def submit_exam_for_classroom(self, classroom_id, exam_id, student_id, data):
        exam = self.get_exam_for_classroom_submission(classroom_id, exam_id)
        self.assert_student_membership(classroom_id, student_id)
        return self.submit_exam_with_exam(exam, student_id, data)

    def get_submission(self, uid):
        submission = self.submission_repo.get_by_uid(uid)
        if not submission:
            raise ValueError("Submission not found")
        return submission

    def get_my_submission(self, exam_id, student_id):
        submissions = self.submission_repo.list_by_exam_and_student(exam_id, student_id)
        if not submissions:
            raise ValueError("Submission not found")
        return submissions[0]

    def get_my_submission_for_classroom(self, classroom_id, exam_id, student_id):
        exam = self.get_exam_for_classroom_submission(classroom_id, exam_id)
        self.assert_student_membership(classroom_id, student_id)
        submissions = self.submission_repo.list_by_exam_and_student(exam.uid, student_id)
        return submissions[0] if submissions else None

    def list_exam_submissions(self, exam_id, teacher_id):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        return self.submission_repo.list_by_exam(exam_id)

    def get_teacher_submission(self, submission_id, teacher_id):
        submission = self.get_submission(submission_id)
        exam = self.exam_repo.get_by_uid(submission.exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        return submission

    def grade_submission(self, submission_id, teacher_id, data):
        submission = self.get_teacher_submission(submission_id, teacher_id)
        update_data = {}

        if "grade" in data:
            update_data["grade"] = float(data["grade"])

        if "feedback" in data:
            update_data["feedback"] = data.get("feedback") or ""

        update_data["graded_by"] = teacher_id
        update_data["graded_at"] = datetime.utcnow()
        update_data["status"] = "graded"

        return self.submission_repo.update(submission, **update_data)
