import json as _json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.course.exam.serializers import (
    ExamSubmissionAIGradeSerializer,
    ExamSubmissionGradeSerializer,
    serialize_exam_submission,
)
from features.course.exam.services import ExamService, ExamSubmissionService, ExamSessionService
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService


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


def _serialize_session(session):
    return {
        "uid": str(session.uid),
        "exam_id": str(session.exam_id),
        "student_id": str(session.student_id),
        "token": session.token,
        "token_status": session.token_status,
        "token_expires_at": session.token_expires_at.isoformat() if session.token_expires_at else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ends_at": session.ends_at.isoformat() if session.ends_at else None,
    }


def _serialize_ai_grade_batch(results):
    graded = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    return {
        "total": len(results),
        "graded": len(graded),
        "failed": len(failed),
        "results": [
            {
                "success": r["success"],
                "error": r["error"],
                "submission": serialize_exam_submission(r["submission"]),
            }
            for r in results
        ],
    }


def _submission_error_response(exc):
    message = str(exc)
    code = status.HTTP_400_BAD_REQUEST
    if message in {"Exam not found", "Resource not found"}:
        code = status.HTTP_404_NOT_FOUND
    elif message in {
        "Student is not a member of this classroom",
        "Resource does not belong to this student",
    }:
        code = status.HTTP_403_FORBIDDEN
    return Response({"error": message}, status=code)


class SpaceExamViewSet(ViewSet):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exam_service = ExamService()
        self.submission_service = ExamSubmissionService()
        self.session_service = ExamSessionService()

    # ── EXAM CRUD ─────────────────────────────────────────────────────────────

    def list(self, request):
        classroom_id = request.query_params.get("classroom_id")
        status = request.query_params.getlist("status") or request.query_params.get("status") or None
        exam_mode = request.query_params.get("exam_mode") or None
        exams = self.exam_service.list_teacher_exams(
            teacher_id=request.user.uid,
            classroom_id=classroom_id,
            status=status,
            exam_mode=exam_mode,
        )
        return Response([_serialize_exam(e) for e in exams])

    def retrieve(self, request, uid=None):
        return Response(_serialize_exam(self.exam_service.get_exam(uid)))

    def create(self, request):
        exam = self.exam_service.create_exam(request.user.uid, request.data.copy())
        ClassroomActivityLogService().log(
            classroom_uid=exam.classroom_id,
            log_level='major',
            event_type='exam_created',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=exam.uid,
            target_name=exam.title,
        )
        return Response(_serialize_exam(exam), status=status.HTTP_201_CREATED)

    def update(self, request, uid=None):
        prev_status = None
        try:
            prev_status = self.exam_service.get_exam(uid).status
        except Exception:
            pass
        exam = self.exam_service.update_exam(uid, request.data.copy())
        new_status = request.data.get('status')
        if new_status == 'published' and prev_status != 'published':
            ClassroomActivityLogService().log(
                classroom_uid=exam.classroom_id,
                log_level='major',
                event_type='exam_published',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=exam.uid,
                target_name=exam.title,
            )
        return Response(_serialize_exam(exam))

    def destroy(self, request, uid=None):
        try:
            exam = self.exam_service.get_exam(uid)
            classroom_id = exam.classroom_id
            exam_title = exam.title
        except Exception:
            classroom_id = None
            exam_title = ''
        self.exam_service.delete_exam(uid)
        if classroom_id:
            ClassroomActivityLogService().log(
                classroom_uid=classroom_id,
                log_level='detail',
                event_type='exam_deleted',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=uid,
                target_name=exam_title,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── SUBMISSIONS (exam-scoped) ──────────────────────────────────────────────

    def list_submissions(self, request, exam_uid=None):
        submissions = self.submission_service.list_exam_submissions(
            exam_id=exam_uid,
            teacher_id=request.user.uid,
        )
        return Response([serialize_exam_submission(s) for s in submissions])

    def ai_grade_exam_submissions(self, request, exam_uid=None):
        serializer = ExamSubmissionAIGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            results = self.submission_service.ai_grade_exam_submissions(
                exam_id=exam_uid,
                teacher_id=request.user.uid,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return _submission_error_response(exc)
        return Response(_serialize_ai_grade_batch(results))

    # ── SUBMISSIONS (submission-scoped) ───────────────────────────────────────

    def get_submission(self, request, submission_uid=None):
        submission = self.submission_service.get_teacher_submission(
            submission_id=submission_uid,
            teacher_id=request.user.uid,
        )
        return Response(serialize_exam_submission(submission))

    def grade_submission(self, request, submission_uid=None):
        serializer = ExamSubmissionGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = self.submission_service.grade_submission(
            submission_id=submission_uid,
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(serialize_exam_submission(submission))

    def ai_grade_submission(self, request, submission_uid=None):
        serializer = ExamSubmissionAIGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = self.submission_service.ai_grade_submission(
                submission_id=submission_uid,
                teacher_id=request.user.uid,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return _submission_error_response(exc)
        return Response(serialize_exam_submission(submission))

    # ── ONLINE SESSION MANAGEMENT ─────────────────────────────────────────────

    def open_online(self, request, uid=None):
        try:
            late_threshold = int(request.data.get("late_threshold_seconds", 0))
            duration = request.data.get("duration_seconds")
            camera_required = request.data.get("camera_required")

            if duration is not None:
                duration = int(duration)
            if duration is None or duration <= 0:
                return Response(
                    {"error": "duration_seconds is required and must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sessions, exam = self.session_service.open_online(
                uid,
                request.user.uid,
                late_threshold_seconds=late_threshold,
                duration_seconds=duration,
                camera_required=camera_required,
            )
            ClassroomActivityLogService().log(
                classroom_uid=exam.classroom_id,
                log_level='major',
                event_type='exam_opened',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=exam.uid,
                target_name=exam.title,
                metadata={'sessions_count': len(sessions)},
            )
            return Response({
                "exam": _serialize_exam(exam),
                "sessions": [_serialize_session(s) for s in sessions],
                "expires_in_minutes": ExamSessionService.LINK_TTL_MINUTES,
            })
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def close_online(self, request, uid=None):
        try:
            self.session_service.close_online(uid, request.user.uid)
            try:
                exam = self.exam_service.get_exam(uid)
                ClassroomActivityLogService().log(
                    classroom_uid=exam.classroom_id,
                    log_level='major',
                    event_type='exam_closed',
                    actor_id=request.user.uid,
                    actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                    actor_role='teacher',
                    target_id=exam.uid,
                    target_name=exam.title,
                )
            except Exception:
                pass
            return Response({"message": "Online session closed"})
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def list_online_sessions(self, request, uid=None):
        try:
            sessions = self.session_service.list_by_exam(uid, request.user.uid)
            return Response([_serialize_session(s) for s in sessions])
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    # ── CLASSROOM-SCOPED AI GRADE ──────────────────────────────────────────────

    def ai_grade_classroom_submissions(self, request, classroom_uid=None):
        serializer = ExamSubmissionAIGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = self.submission_service.ai_grade_classroom_submissions(
            classroom_id=classroom_uid,
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        return Response(_serialize_ai_grade_batch(results))
