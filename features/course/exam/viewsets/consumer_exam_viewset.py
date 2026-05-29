import json as _json
from datetime import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.serializers import (
    ExamSubmissionRequestSerializer,
    serialize_exam_submission,
)
from features.course.exam.services import ExamService, ExamSubmissionService, ExamSessionService


def _parse_meta(raw) -> dict:
    try:
        return _json.loads(raw or '{}')
    except Exception:
        return {}


def _serialize_exam(exam):
    return {
        "uid": str(exam.uid),
        "classroom_id": str(exam.classroom_id),
        "teacher_id": str(exam.teacher_id),
        "title": exam.title,
        "description": exam.description,
        "exam_type": getattr(exam, "exam_type", None) or "assignment",
        "max_grade": getattr(exam, "max_grade", None) or 10.0,
        "content_type": exam.content_type,
        "body": exam.body or "",
        "ref_id": str(exam.ref_id) if exam.ref_id else None,
        "meta": _parse_meta(exam.meta),
        "status": exam.status,
        "is_online_active": bool(exam.is_online_active),
        "opened_at": exam.opened_at.isoformat() if exam.opened_at else None,
        "late_threshold_seconds": exam.late_threshold_seconds,
        "camera_required": bool(exam.camera_required),
        "exam_mode": exam.exam_mode,
        "duration_seconds": exam.duration_seconds if exam.duration_seconds else 0,
        "due_date": exam.due_date.isoformat() if exam.due_date else None,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "updated_at": exam.updated_at.isoformat() if exam.updated_at else None,
    }


def _submission_error_response(exc):
    message = str(exc)
    code = status.HTTP_400_BAD_REQUEST
    if message in {"Exam not found", "Resource not found"}:
        code = status.HTTP_404_NOT_FOUND
    elif message in {
        "Student is not a member of this classroom",
        "Resource does not belong to this student",
        "Camera monitoring is required for this exam",
        "No active exam session. Please join via your exam link.",
        "Your exam time has expired",
        "Your exam session is no longer active",
    }:
        code = status.HTTP_403_FORBIDDEN
    return Response({"error": message}, status=code)


class ConsumerExamViewSet(ViewSet):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exam_service = ExamService()
        self.submission_service = ExamSubmissionService()
        self.session_service = ExamSessionService()
        self.member_repo = ClassroomMemberRepository()

    def list_classroom_exams(self, request, uid=None):
        exams = self.exam_service.list_student_exams(uid)
        return Response([_serialize_exam(e) for e in exams])

    def submit(self, request, exam_uid=None):
        serializer = ExamSubmissionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission, created = self.submission_service.submit_exam(
                exam_id=exam_uid,
                student_id=request.user.uid,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return _submission_error_response(exc)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serialize_exam_submission(submission), status=response_status)

    def my_submission(self, request, exam_uid=None):
        try:
            submission = self.submission_service.get_my_submission(
                exam_id=exam_uid,
                student_id=request.user.uid,
            )
        except ValueError as exc:
            if str(exc) == "Submission not found":
                return Response(None, status=status.HTTP_200_OK)
            return _submission_error_response(exc)
        return Response(serialize_exam_submission(submission))

    def join_session(self, request, token=None):
        try:
            session, exam = self.session_service.join(token, request.user.uid)
        except ValueError as exc:
            msg = str(exc)
            code = (
                status.HTTP_403_FORBIDDEN
                if "expired" in msg or "belong" in msg or "valid" in msg
                else status.HTTP_404_NOT_FOUND
            )
            return Response({"error": msg}, status=code)

        now_ts = datetime.utcnow()
        time_remaining = None
        if session.ends_at:
            diff = (session.ends_at - now_ts).total_seconds()
            time_remaining = max(0, int(diff))

        return Response({
            "exam": _serialize_exam(exam),
            "session": {
                "uid": str(session.uid),
                "token_status": session.token_status,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "ends_at": session.ends_at.isoformat() if session.ends_at else None,
                "time_remaining_seconds": time_remaining,
            },
        })

    def get_quiz_questions(self, request, exam_uid=None):
        from features.quiz.repositories.quiz_question_repository import QuizQuestionRepository

        try:
            exam = self.exam_service.get_exam(exam_uid)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        exam_type = getattr(exam, "exam_type", None) or "assignment"
        if exam_type != "quiz":
            return Response({"error": "This exam is not a quiz"}, status=status.HTTP_400_BAD_REQUEST)

        ref_id = getattr(exam, "ref_id", None)
        if not ref_id or exam.content_type != "quiz":
            return Response({"error": "This exam has no quiz linked"}, status=status.HTTP_400_BAD_REQUEST)

        if not self.member_repo.is_member(exam.classroom_id, request.user.uid):
            return Response({"error": "You are not a member of this classroom"}, status=status.HTTP_403_FORBIDDEN)

        questions = list(QuizQuestionRepository().get_by_quiz(ref_id))
        questions.sort(key=lambda q: q.order)

        safe_questions = [
            {
                "uid": str(q.uid),
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "order": q.order,
            }
            for q in questions
        ]

        return Response({
            "exam_uid": str(exam.uid),
            "title": exam.title,
            "total_questions": len(safe_questions),
            "duration_seconds": exam.duration_seconds or 0,
            "max_grade": getattr(exam, "max_grade", None) or 10.0,
            "ref_id": str(ref_id),
            "questions": safe_questions,
        })

    def my_session(self, request, exam_uid=None):
        session = self.session_service.get_my_session(exam_uid, request.user.uid)
        if not session:
            return Response(None)
        now_ts = datetime.utcnow()
        time_remaining = None
        if session.ends_at:
            diff = (session.ends_at - now_ts).total_seconds()
            time_remaining = max(0, int(diff))
        return Response({
            "uid": str(session.uid),
            "token": session.token,
            "token_status": session.token_status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ends_at": session.ends_at.isoformat() if session.ends_at else None,
            "time_remaining_seconds": time_remaining,
        })
