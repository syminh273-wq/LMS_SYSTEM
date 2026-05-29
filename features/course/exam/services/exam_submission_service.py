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
    ASSIGNMENT_ALLOWED_FILE_TYPES = {"pdf", "docx", "zip", "jpg", "jpeg", "png"}

    def __init__(self):
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.member_repo = ClassroomMemberRepository()
        self.resource_repo = ResourceRepository()
        self.ai_grading_service = ExamAIGradingService()

    def validate_content(self, data, student_id=None):
        import json
        content_type = data.get("content_type")

        if content_type == "quiz":
            answers = data.get("answers")
            if not isinstance(answers, dict):
                raise ValueError("answers must be a dict of {question_uid: letter} for quiz submission")
            data["body"] = json.dumps({"answers": answers})
            data["ref_id"] = None
            data["meta"] = "{}"
            return data

        if content_type == self.MARKDOWN:
            body = data.get("body") or data.get("content", "")
            if not body:
                raise ValueError("body is required when content_type is markdown")
            data["body"] = body
            data["ref_id"] = None
            data["meta"] = "{}"
            return data

        if content_type in self.FILE_TYPES:
            ref_id = data.get("ref_id") or data.get("resource_uid")
            if not ref_id:
                raise ValueError("ref_id (resource) is required when content_type is file/pdf/image")

            try:
                resource = self.resource_repo.find(ref_id)
            except self.resource_repo.model.DoesNotExist:
                raise ValueError("Resource not found")

            if student_id and str(resource.owner_id) != str(student_id):
                raise ValueError("Resource does not belong to this student")

            data["body"] = ""
            data["ref_id"] = ref_id
            data["meta"] = json.dumps({"url": resource.url, "name": resource.name}, ensure_ascii=False)
            return data

        raise ValueError("Invalid content_type")

    def validate_status(self, status):
        if status not in self.STATUSES:
            raise ValueError("Invalid status")

    def load_quiz_questions(self, ref_id):
        from features.quiz.repositories.quiz_question_repository import QuizQuestionRepository
        return list(QuizQuestionRepository().get_by_quiz(ref_id))

    def auto_grade_quiz(self, exam, answers: dict) -> dict:
        questions = self.load_quiz_questions(exam.ref_id)
        if not questions:
            return {"grade": 0.0, "correct_count": 0, "total": 0, "feedback": "0/0 correct"}

        total = len(questions)
        correct_count = sum(
            1 for q in questions
            if str(q.uid) in answers and answers[str(q.uid)] == q.correct_answer
        )
        max_grade = float(exam.max_grade or 10.0)
        grade = round((correct_count / total) * max_grade, 2)
        return {
            "grade": grade,
            "correct_count": correct_count,
            "total": total,
            "feedback": f"{correct_count}/{total} correct",
        }

    def assert_no_existing_quiz_submission(self, exam, student_id):
        existing = self.submission_repo.list_by_exam_and_student(exam.uid, student_id)
        if existing:
            raise ValueError("You have already submitted this quiz")

    def assert_assignment_file_type(self, exam, data):
        if getattr(exam, 'exam_type', 'assignment') != 'assignment':
            return
        ref_id = data.get("ref_id") or data.get("resource_uid")
        if not ref_id:
            return
        try:
            resource = self.resource_repo.find(ref_id)
        except Exception:
            return
        file_ext = (getattr(resource, 'file_type', '') or '').lower().lstrip('.')
        if file_ext and file_ext not in self.ASSIGNMENT_ALLOWED_FILE_TYPES:
            raise ValueError("File type not allowed. Accepted: PDF, DOCX, ZIP, JPG, PNG")

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

    def assert_camera_session(self, exam, student_id):
        if not exam.camera_required:
            return
        from datetime import datetime, timedelta
        from features.face.models import FaceVerificationLog
        recent_cutoff = datetime.utcnow() - timedelta(minutes=2)
        logs = list(
            FaceVerificationLog.objects.filter(
                exam_id=exam.uid,
                student_id=student_id,
            ).allow_filtering()
        )
        if not logs:
            raise ValueError("Camera monitoring is required for this exam. Please enable your camera.")
        recent_recognized = any(
            log.recognized and log.verified_at and log.verified_at >= recent_cutoff
            for log in logs
        )
        if not recent_recognized:
            raise ValueError("Camera verification has stopped. Please ensure your face is visible before submitting.")

    def assert_online_session(self, exam, student_id):
        if exam.exam_mode != 'online':
            return
        from features.course.exam.services.exam_session_service import ExamSessionService
        svc = ExamSessionService()
        svc.validate_for_submit(exam.uid, student_id)

    def submit_exam(self, exam_id, student_id, data):
        import json
        exam = self.get_exam_for_submission(exam_id)
        self.assert_student_membership(exam.classroom_id, student_id)
        self.assert_camera_session(exam, student_id)
        self.assert_online_session(exam, student_id)

        exam_type = getattr(exam, 'exam_type', 'assignment') or 'assignment'

        if exam_type == 'quiz':
            self.assert_no_existing_quiz_submission(exam, student_id)
        else:
            self.assert_assignment_file_type(exam, data)

        data = self.validate_content(data, student_id=student_id)
        data["exam_id"] = exam.uid
        data["classroom_id"] = exam.classroom_id
        data["student_id"] = student_id
        data["submitted_at"] = datetime.utcnow()

        if exam_type == 'quiz':
            answers = json.loads(data["content"]).get("answers", {})
            grade_result = self.auto_grade_quiz(exam, answers)
            data["content"] = json.dumps({
                "answers": answers,
                "correct_count": grade_result["correct_count"],
                "total": grade_result["total"],
            })
            data["status"] = "graded"
            data["grade"] = grade_result["grade"]
            data["feedback"] = grade_result["feedback"]
            data["graded_at"] = datetime.utcnow()
            data["grading_method"] = "auto"
            result_submission = self.submission_repo.create(**data)
            created = True
        else:
            existing = self.submission_repo.list_by_exam_and_student(exam.uid, student_id)
            data["status"] = self.build_submission_status(exam)

            if existing:
                data["grade"] = None
                data["feedback"] = ""
                data["graded_by"] = None
                data["graded_at"] = None
                result_submission, created = self.submission_repo.update(existing[0], **data), False
            else:
                result_submission, created = self.submission_repo.create(**data), True

        # Complete online session after successful submission
        session_for_audit = None
        if exam.exam_mode == 'online':
            try:
                from features.course.exam.services.exam_session_service import ExamSessionService
                svc = ExamSessionService()
                session_for_audit = svc.get_my_session(exam.uid, student_id)
                svc.complete(exam.uid, student_id)
            except Exception:
                pass

        # Audit log
        try:
            from features.course.exam.repositories.exam_audit_log_repository import ExamAuditLogRepository
            now_ts = datetime.utcnow()
            is_timeout = bool(
                session_for_audit and
                session_for_audit.ends_at and
                now_ts > session_for_audit.ends_at
            )
            ExamAuditLogRepository().log(
                exam_id=exam.uid,
                student_id=student_id,
                event_type='timeout_submit' if is_timeout else 'submitted',
                event_data={'submitted_at': now_ts.isoformat()},
            )
        except Exception:
            pass

        return result_submission, created

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
