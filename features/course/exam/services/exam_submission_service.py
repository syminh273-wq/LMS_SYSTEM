from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone

from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository
from features.course.exam.services.exam_ai_grading_service import ExamAIGradingService
from features.resource.repositories import ResourceRepository


class ExamSubmissionService:
    MARKDOWN = "markdown"
    FILE_TYPES = ["pdf", "image", "file"]
    STATUSES = ["submitted", "late", "graded", "returned"]

    def __init__(self):
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.member_repo = ClassroomMemberRepository()
        self.resource_repo = ResourceRepository()
        self.ai_grading_service = ExamAIGradingService()

    def validate_content(self, data, student_id=None):
        content_type = data.get("content_type")

        if content_type == self.MARKDOWN:
            if not data.get("content"):
                raise ValueError("content is required when content_type is markdown")
            data["resource_uid"] = None
            data["resource_url"] = ""
            data["resource_name"] = ""
            return data

        if content_type in self.FILE_TYPES:
            resource_uid = data.get("resource_uid")
            if not resource_uid:
                raise ValueError("resource_uid is required when content_type is file/pdf/image")

            try:
                resource = self.resource_repo.find(resource_uid)
            except self.resource_repo.model.DoesNotExist:
                raise ValueError("Resource not found")

            if student_id and str(resource.owner_id) != str(student_id):
                raise ValueError("Resource does not belong to this student")

            data["content"] = ""
            data["resource_url"] = resource.url
            data["resource_name"] = resource.name
            return data

        raise ValueError("Invalid content_type")

    def validate_status(self, status):
        if status not in self.STATUSES:
            raise ValueError("Invalid status")

    def get_exam_for_submission(self, exam_id):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if exam.status != "published":
            raise ValueError("Exam is not open for submissions")
        return exam

    def assert_student_membership(self, classroom_id, student_id):
        if not self.member_repo.is_member(classroom_id, student_id):
            raise ValueError("Student is not a member of this classroom")

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
        update_data["grading_method"] = "manual"

        return self.submission_repo.update(submission, **update_data)

    def ai_grade_submission(self, submission_id, teacher_id, data):
        submission = self.get_teacher_submission(submission_id, teacher_id)
        if submission.grade is not None and not data.get("overwrite", False):
            raise ValueError("Submission already graded")

        exam = self.exam_repo.get_by_uid(submission.exam_id)
        if not exam:
            raise ValueError("Exam not found")

        result = self.ai_grading_service.grade(
            exam=exam,
            submission=submission,
            rubric=data.get("rubric") or "",
            max_grade=float(data.get("max_grade") or 10),
            top_k=int(data.get("top_k") or 5),
        )

        return self.submission_repo.update(
            submission,
            grade=result["grade"],
            feedback=result["feedback"],
            graded_by=teacher_id,
            graded_at=result["graded_at"],
            status="graded",
            grading_method="ai",
            ai_model=result["model"],
            ai_rubric=data.get("rubric") or "",
            ai_reason=result["reason"],
            ai_breakdown=self._to_json(result["breakdown"]),
            ai_sources=self._to_json(result["sources"]),
            ai_confidence=result["confidence"],
        )

    def ai_grade_exam_submissions(self, exam_id, teacher_id, data):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")

        submissions = self.submission_repo.list_by_exam(exam.uid)
        return self._ai_grade_many(submissions, teacher_id, data)

    def ai_grade_classroom_submissions(self, classroom_id, teacher_id, data):
        exams = self.exam_repo.list_by_teacher(teacher_id)
        classroom_exams = [exam for exam in exams if str(exam.classroom_id) == str(classroom_id)]

        submissions = []
        for exam in classroom_exams:
            submissions.extend(list(self.submission_repo.list_by_exam(exam.uid)))

        return self._ai_grade_many(submissions, teacher_id, data)

    def _ai_grade_many(self, submissions, teacher_id, data):
        results = []
        for submission in submissions:
            try:
                updated = self.ai_grade_submission(submission.uid, teacher_id, data)
                results.append({"submission": updated, "success": True, "error": ""})
            except ValueError as exc:
                results.append({"submission": submission, "success": False, "error": str(exc)})
            except Exception as exc:
                results.append({"submission": submission, "success": False, "error": str(exc)})
        return results

    def _to_json(self, value):
        import json

        return json.dumps(value, ensure_ascii=False)
