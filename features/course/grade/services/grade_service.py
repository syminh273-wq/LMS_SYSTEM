import json
import math
import re
from datetime import datetime

from core.ai.llm.services.omni_route_client import OmniRouteClient
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository
from features.course.grade.repositories import GradeRepository


class GradeService:
    AI_ROLE = "ai"
    TEACHER_ROLE = "teacher"
    SUGGESTED = "suggested"
    FINAL = "final"

    def __init__(self):
        self.grade_repo = GradeRepository()
        self.exam_repo = ExamRepository()
        self.submission_repo = ExamSubmissionRepository()

    def get_teacher_submission(self, submission_id, teacher_id):
        submission = self.submission_repo.get_by_uid(submission_id)
        if not submission:
            raise ValueError("Submission not found")

        exam = self.exam_repo.get_by_uid(submission.exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise PermissionError("You do not own this exam")
        return exam, submission

    def list_submission_grades(self, submission_id, teacher_id):
        self.get_teacher_submission(submission_id, teacher_id)
        return self.grade_repo.list_by_submission(submission_id)

    def ai_grade_submission(self, submission_id, teacher_id, data):
        exam, submission = self.get_teacher_submission(submission_id, teacher_id)
        if submission.content_type != "markdown" or not submission.content:
            raise ValueError("AI grading currently supports markdown submissions only")

        max_score = self._get_exam_max_score(exam)
        messages = self._build_ai_messages(
            exam=exam,
            submission=submission,
            rubric=data.get("rubric", ""),
            max_score=max_score,
        )
        raw = OmniRouteClient.chat_sync(
            messages,
            models=OmniRouteClient.TEXT_MODELS,
            timeout=90,
        )
        result = self._parse_ai_result(raw, max_score)

        return self.grade_repo.create(
            submission_id=submission.uid,
            exam_id=submission.exam_id,
            classroom_id=submission.classroom_id,
            student_id=submission.student_id,
            grader_role=self.AI_ROLE,
            score=result["score"],
            max_score=max_score,
            feedback=result["feedback"],
            status=self.SUGGESTED,
            ai_model=",".join(OmniRouteClient.TEXT_MODELS),
        )

    def teacher_grade_submission(self, submission_id, teacher_id, data):
        exam, submission = self.get_teacher_submission(submission_id, teacher_id)
        source_grade = self._get_ai_suggestion(
            data.get("ai_grade_uid"),
            submission.uid,
        )

        score = data.get("score", data.get("grade"))
        if score is None and source_grade:
            score = source_grade.score
        if score is None:
            raise ValueError("score is required without an AI suggestion")

        score = float(score)
        max_score = self._get_exam_max_score(exam)
        if not math.isfinite(score):
            raise ValueError("score must be a finite number")
        if score < 0 or score > max_score:
            raise ValueError(f"score must be between 0 and {max_score}")

        feedback = data.get("feedback")
        if feedback is None and source_grade:
            feedback = source_grade.feedback

        grade = self.grade_repo.create(
            submission_id=submission.uid,
            exam_id=submission.exam_id,
            classroom_id=submission.classroom_id,
            student_id=submission.student_id,
            grader_role=self.TEACHER_ROLE,
            grader_id=teacher_id,
            score=score,
            max_score=max_score,
            feedback=feedback or "",
            status=self.FINAL,
        )
        updated_submission = self.submission_repo.update(
            submission,
            grade=score,
            feedback=feedback or "",
            graded_by=teacher_id,
            graded_at=datetime.utcnow(),
            status="graded",
        )
        return grade, updated_submission

    def _get_exam_max_score(self, exam):
        max_score = float(exam.max_score if exam.max_score is not None else 10.0)
        if not math.isfinite(max_score) or max_score <= 0:
            raise ValueError("Exam max_score is invalid")
        return max_score

    def _get_ai_suggestion(self, grade_uid, submission_uid):
        if not grade_uid:
            return None
        grade = self.grade_repo.get_by_uid(grade_uid)
        if (
            not grade
            or str(grade.submission_id) != str(submission_uid)
            or grade.grader_role != self.AI_ROLE
        ):
            raise ValueError("AI grade suggestion not found")
        return grade

    def _build_ai_messages(self, exam, submission, rubric, max_score):
        instructions = {
            "task": "Evaluate the student answer against the exam prompt.",
            "score_range": f"0 to {max_score}",
            "rules": [
                "Use only the supplied exam prompt, answer, and rubric.",
                "Be objective and explain missing or incorrect elements.",
                "Return JSON only with keys score and feedback.",
            ],
        }
        prompt = (
            f"Exam title: {exam.title}\n"
            f"Exam prompt: {exam.description}\n{exam.content}\n\n"
            f"Teacher rubric: {rubric or 'No additional rubric supplied.'}\n\n"
            f"Student answer:\n{submission.content}"
        )
        return [
            {"role": "system", "content": json.dumps(instructions)},
            {"role": "user", "content": prompt},
        ]

    def _parse_ai_result(self, raw, max_score):
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        start, end = clean.find("{"), clean.rfind("}")
        if start < 0 or end < start:
            raise ValueError("AI did not return valid grading JSON")
        try:
            parsed = json.loads(clean[start : end + 1])
            score = float(parsed["score"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("AI did not return valid grading JSON")

        if not math.isfinite(score) or score < 0 or score > max_score:
            raise ValueError("AI returned a score outside the allowed range")
        feedback = str(parsed.get("feedback", "")).strip()
        if not feedback:
            raise ValueError("AI did not return feedback")
        return {"score": score, "feedback": feedback}
