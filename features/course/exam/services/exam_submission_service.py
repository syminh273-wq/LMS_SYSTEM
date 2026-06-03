import json
from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone

from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository
from features.course.exam.services.exam_ai_grading_service import ExamAIGradingService
from features.resource.repositories import ResourceRepository


class ExamSubmissionService:
    STATUSES = ["submitted", "late", "graded", "returned"]

    def __init__(self):
        self.exam_repo       = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()
        self.member_repo     = ClassroomMemberRepository()
        self.resource_repo   = ResourceRepository()
        self.ai_grading_service = ExamAIGradingService()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _quiz_log_service(self):
        from features.quiz.services.quiz_log_service import QuizLogService
        return QuizLogService()

    def get_exam_for_submission(self, exam_id):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if exam.status not in ("published", "ongoing"):
            raise ValueError("Exam is not open for submissions")
        return exam

    def assert_student_membership(self, classroom_id, student_id):
        if not self.member_repo.is_member(classroom_id, student_id):
            raise ValueError("Student is not a member of this classroom")

    def assert_no_existing_mc_submission(self, exam, student_id):
        existing = self.submission_repo.list_by_exam_and_student(exam.uid, student_id)
        if existing:
            raise ValueError("You have already submitted this quiz")

    def assert_camera_session(self, exam, student_id):
        if not exam.camera_required:
            return
        from datetime import timedelta
        from features.face.models import FaceVerificationLog
        recent_cutoff = datetime.utcnow() - timedelta(minutes=2)
        logs = list(FaceVerificationLog.objects.filter(exam_id=exam.uid, student_id=student_id).allow_filtering())
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
        ExamSessionService().validate_for_submit(exam.uid, student_id)

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

    # ── Prepare submission data based on type ──────────────────────────────────

    def prepare_submission(self, exam, student_id, data: dict) -> dict:
        submission_type = data.get("submission_type")

        if submission_type in ("multiple_choice", "online_quiz"):
            answers = data.get("answers") or {}
            if not isinstance(answers, dict):
                raise ValueError("answers must be a dict of {question_uid: letter}")

            quiz_id = getattr(exam, "ref_id", None)
            if not quiz_id:
                raise ValueError("This exam has no quiz linked")

            svc = self._quiz_log_service()
            attempt_number = svc.count_attempts(quiz_id, exam.classroom_id, student_id) + 1
            quiz_log, correct_count, total, score_pct, score = svc.create(
                quiz_id=quiz_id,
                classroom_id=exam.classroom_id,
                student_id=student_id,
                answers=answers,
                time_taken_seconds=data.get("time_taken_seconds", 0),
                max_grade=float(exam.max_grade or 10.0),
                attempt_number=attempt_number,
                source="exam",
                exam_id=exam.uid,
            )
            # Build per-question result breakdown
            from features.quiz.repositories.quiz_question_repository import QuizQuestionRepository
            questions = list(QuizQuestionRepository().get_by_quiz(quiz_id))
            questions.sort(key=lambda q: q.order)
            results = []
            for q in questions:
                q_uid = str(q.uid)
                chosen = answers.get(q_uid)
                is_correct = bool(chosen and chosen == q.correct_answer)
                results.append({
                    "question_uid":  q_uid,
                    "question_text": q.question_text,
                    "chosen":        chosen,
                    "correct_answer": q.correct_answer,
                    "is_correct":    is_correct,
                    "explanation":   q.explanation or "",
                })

            data["ref_id"]  = quiz_log.uid
            data["content"] = ""
            data["meta"]    = json.dumps({
                "correct_count": correct_count,
                "total":         total,
                "score_pct":     score_pct,
                "results":       results,
            })
            data["grade"]          = score
            data["max_grade"]      = float(exam.max_grade or 10.0)
            data["passed"]         = score_pct >= 50
            data["grading_method"] = "auto"
            data["graded_at"]      = datetime.utcnow()
            data["status"]         = "graded"

        elif submission_type == "file":
            ref_id = data.get("ref_id")
            if not ref_id:
                raise ValueError("ref_id (resource uid) is required for file submission")
            try:
                resource = self.resource_repo.find(ref_id)
            except Exception:
                raise ValueError("Resource not found")
            if student_id and str(resource.owner_id) != str(student_id):
                raise ValueError("Resource does not belong to this student")
            data["content"] = ""
            data["meta"]    = json.dumps({
                "url":  resource.url,
                "name": resource.name,
                "size": getattr(resource, "size", 0) or 0,
            })

        elif submission_type == "essay":
            body = data.get("content", "").strip()
            if not body:
                raise ValueError("content is required for essay submission")
            data["ref_id"]  = None
            data["content"] = body
            data["meta"]    = "{}"

        else:
            raise ValueError(
                "submission_type must be one of: multiple_choice, online_quiz, file, essay"
            )

        return data

    # ── Main submit ────────────────────────────────────────────────────────────

    def submit_exam(self, exam_id, student_id, data: dict):
        exam = self.get_exam_for_submission(exam_id)
        self.assert_student_membership(exam.classroom_id, student_id)
        self.assert_camera_session(exam, student_id)
        self.assert_online_session(exam, student_id)

        submission_type = data.get("submission_type", "file")
        is_mc = submission_type in ("multiple_choice", "online_quiz")

        if is_mc:
            self.assert_no_existing_mc_submission(exam, student_id)

        data = self.prepare_submission(exam, student_id, data)
        data["exam_id"]      = exam.uid
        data["classroom_id"] = exam.classroom_id
        data["student_id"]   = student_id
        data["submitted_at"] = datetime.utcnow()

        if not is_mc:
            data.setdefault("status", self.build_submission_status(exam))

        # Complete online session after submission
        session_for_audit = None
        if exam.exam_mode == 'online':
            try:
                from features.course.exam.services.exam_session_service import ExamSessionService
                svc = ExamSessionService()
                session_for_audit = svc.get_my_session(exam.uid, student_id)
                svc.complete(exam.uid, student_id)
            except Exception:
                pass

        # Strip request-only fields that are not ExamSubmission model columns
        for _field in ('time_taken_seconds', 'answers'):
            data.pop(_field, None)

        # Create or update (MC: always create; file/essay: upsert)
        if is_mc:
            result_submission = self.submission_repo.create(**data)
            created = True
        else:
            existing = self.submission_repo.list_by_exam_and_student(exam.uid, student_id)
            if existing:
                data["grade"]      = None
                data["feedback"]   = ""
                data["graded_by"]  = None
                data["graded_at"]  = None
                result_submission  = self.submission_repo.update(existing[0], **data)
                created            = False
            else:
                result_submission = self.submission_repo.create(**data)
                created           = True

        # Audit log
        try:
            from features.course.exam.repositories.exam_audit_log_repository import ExamAuditLogRepository
            now_ts = datetime.utcnow()
            is_timeout = bool(
                session_for_audit and session_for_audit.ends_at and
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

    # ── Read ───────────────────────────────────────────────────────────────────

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

    # ── Teacher grading ────────────────────────────────────────────────────────

    def get_teacher_submission(self, submission_id, teacher_id):
        submission = self.get_submission(submission_id)
        exam = self.exam_repo.get_by_uid(submission.exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        return submission

    def grade_submission(self, submission_id, teacher_id, data: dict):
        submission = self.get_teacher_submission(submission_id, teacher_id)
        update_data = {}
        if "grade" in data:
            update_data["grade"] = float(data["grade"])
        if "feedback" in data:
            update_data["feedback"] = data.get("feedback") or ""
        update_data["graded_by"]      = teacher_id
        update_data["graded_at"]      = datetime.utcnow()
        update_data["status"]         = "graded"
        update_data["grading_method"] = "manual"
        return self.submission_repo.update(submission, **update_data)

    def ai_grade_submission(self, submission_id, teacher_id, data: dict):
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
            ai_breakdown=json.dumps(result["breakdown"], ensure_ascii=False),
            ai_sources=json.dumps(result["sources"], ensure_ascii=False),
            ai_confidence=result["confidence"],
        )

    def ai_grade_exam_submissions(self, exam_id, teacher_id, data: dict):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")
        return self._ai_grade_many(self.submission_repo.list_by_exam(exam.uid), teacher_id, data)

    def ai_grade_classroom_submissions(self, classroom_id, teacher_id, data: dict):
        exams = self.exam_repo.list_by_teacher(teacher_id)
        classroom_exams = [e for e in exams if str(e.classroom_id) == str(classroom_id)]
        submissions = []
        for exam in classroom_exams:
            submissions.extend(list(self.submission_repo.list_by_exam(exam.uid)))
        return self._ai_grade_many(submissions, teacher_id, data)

    def _ai_grade_many(self, submissions, teacher_id, data: dict):
        results = []
        for sub in submissions:
            try:
                updated = self.ai_grade_submission(sub.uid, teacher_id, data)
                results.append({"submission": updated, "success": True, "error": ""})
            except Exception as exc:
                results.append({"submission": sub, "success": False, "error": str(exc)})
        return results
