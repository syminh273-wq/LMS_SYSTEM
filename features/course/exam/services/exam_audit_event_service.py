import json
import logging
from datetime import datetime

from features.course.exam.repositories import (
    ExamAuditLogRepository,
    ExamRepository,
    ExamSessionRepository,
)

logger = logging.getLogger(__name__)


class ExamAuditEventService:
    """
    Records proctoring / audit events during an online exam.

    Events that count toward the `max_tab_leaves` rule (a leave is anything
    that takes the student's attention away from the exam page):
      - tab_leave      (document.hidden = true)
      - window_blur    (window loses focus)
      - fullscreen_exit

    Events that count toward the `max_face_warnings` rule (camera/face issues):
      - camera_lost           (camera was off)
      - face_not_recognized   (face did not match enrollment)
      - multiple_faces        (more than one person in frame)

    Events that are only logged (informational, do NOT count):
      - tab_return, window_focus
      - network_lost, network_restored
      - context_menu, copy, paste, devtools_open
      - page_unload

    Special events:
      - tab_leave_limit_exceeded    → written when tab counter goes over
      - face_warning_limit_exceeded → written when face counter goes over
      - force_submitted             → written when we force-submit the student
    """

    TAB_LEAVE_EVENTS = {"tab_leave", "window_blur", "fullscreen_exit"}
    FACE_WARNING_EVENTS = {"camera_lost", "face_not_recognized", "multiple_faces"}

    def __init__(self):
        self.session_repo = ExamSessionRepository()
        self.exam_repo = ExamRepository()
        self.audit_repo = ExamAuditLogRepository()

    def record_event(self, session_uid, student_id, event_type, event_data=None):
        """
        Returns a dict:
          {
            "logged": True,
            "warning": bool,        # True if student is at/near the limit but not over
            "count": int,           # current tab_leaves_count (or face_warnings_count)
            "max": int,             # max_tab_leaves (or max_face_warnings, 0 = unlimited)
            "remaining": int | None,
            "force_submitted": bool,
            "submission": {...} | None,
            "rule": "tab_leaves" | "face_warnings" | None,
          }
        """
        event_data = event_data or {}
        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type is required")

        session = self.session_repo.get_by_uid(session_uid)
        if not session:
            raise ValueError("Exam session not found")
        if str(session.student_id) != str(student_id):
            raise ValueError("This session does not belong to you")
        if session.token_status not in ("active", "pending"):
            raise ValueError("Exam session is no longer active")

        exam = self.exam_repo.get_by_uid(session.exam_id)
        if not exam:
            raise ValueError("Exam not found")

        now = datetime.utcnow()

        # Determine which rule this event triggers (if any)
        is_tab_leave = event_type in self.TAB_LEAVE_EVENTS
        is_face_warning = event_type in self.FACE_WARNING_EVENTS

        # Initialise result with tab_leaves info (default fields for the FE)
        result = {
            "logged": True,
            "warning": False,
            "count": session.tab_leaves_count or 0,
            "max": exam.max_tab_leaves if exam.max_tab_leaves is not None else 3,
            "remaining": None,
            "force_submitted": False,
            "submission": None,
            "rule": None,
        }

        # Always log the raw event first
        payload = dict(event_data)
        try:
            self.audit_repo.log(
                exam_id=exam.uid,
                student_id=student_id,
                event_type=event_type,
                event_data=payload,
            )
        except Exception as exc:
            logger.warning(f"ExamAuditEventService: log failed: {exc}")

        # Update last_event_at
        try:
            self.session_repo.update(session, last_event_at=now)
            session = self.session_repo.get_by_uid(session_uid) or session
        except Exception as exc:
            logger.warning(f"ExamAuditEventService: update last_event_at failed: {exc}")

        if is_tab_leave:
            self._increment_and_check(
                session=session,
                session_uid=session_uid,
                exam=exam,
                student_id=student_id,
                rule="tab_leaves",
                event_type=event_type,
                payload=payload,
                now=now,
                current_count=int(getattr(session, "tab_leaves_count", 0) or 0),
                counter_field="tab_leaves_count",
                exceeded_event="tab_leave_limit_exceeded",
                reason="tab_leave_limit_exceeded",
                result=result,
                max_attr="max_tab_leaves",
            )
        elif is_face_warning:
            self._increment_and_check(
                session=session,
                session_uid=session_uid,
                exam=exam,
                student_id=student_id,
                rule="face_warnings",
                event_type=event_type,
                payload=payload,
                now=now,
                current_count=int(getattr(session, "face_warnings_count", 0) or 0),
                counter_field="face_warnings_count",
                exceeded_event="face_warning_limit_exceeded",
                reason="face_warning_limit_exceeded",
                result=result,
                max_attr="max_face_warnings",
            )

        return result

    def _increment_and_check(
        self,
        session,
        session_uid,
        exam,
        student_id,
        rule,
        event_type,
        payload,
        now,
        current_count,
        counter_field,
        exceeded_event,
        reason,
        result,
        max_attr,
    ):
        """Shared logic for tab-leave and face-warning counters."""
        new_count = current_count + 1
        try:
            self.session_repo.update(session, **{counter_field: new_count}, last_event_at=now)
            session = self.session_repo.get_by_uid(session_uid) or session
        except Exception as exc:
            logger.warning(f"ExamAuditEventService: increment {counter_field} failed: {exc}")

        result["count"] = new_count
        result["rule"] = rule
        result["max"] = int(getattr(exam, max_attr, 0) or 0)

        max_allowed = result["max"]

        if max_allowed > 0 and new_count > max_allowed:
            # Log the "limit exceeded" event
            try:
                self.audit_repo.log(
                    exam_id=exam.uid,
                    student_id=student_id,
                    event_type=exceeded_event,
                    event_data={
                        "count": new_count,
                        "max": max_allowed,
                        "triggered_by": event_type,
                        **payload,
                    },
                )
            except Exception:
                pass

            # Build submission payload from snapshot_answers
            submission_payload = {}
            snapshot_answers = payload.get("snapshot_answers")
            if isinstance(snapshot_answers, dict):
                submission_payload["answers"] = snapshot_answers
            submission_payload["snapshot_event_data"] = {
                k: v for k, v in payload.items() if k != "snapshot_answers"
            }

            try:
                from features.course.exam.services.exam_submission_service import (
                    ExamSubmissionService,
                )
                sub_svc = ExamSubmissionService()
                submission, _ = sub_svc.force_submit(
                    exam_id=exam.uid,
                    student_id=student_id,
                    reason=reason,
                    data=submission_payload,
                )
                from features.course.exam.serializers import serialize_exam_submission
                result["submission"] = serialize_exam_submission(submission)
                result["force_submitted"] = True

                try:
                    self.audit_repo.log(
                        exam_id=exam.uid,
                        student_id=student_id,
                        event_type="force_submitted",
                        event_data={
                            "reason": reason,
                            "count": new_count,
                            "max": max_allowed,
                            "rule": rule,
                            "submission_uid": str(submission.uid),
                        },
                    )
                except Exception:
                    pass
            except Exception as exc:
                logger.exception(f"force_submit failed: {exc}")
        else:
            if max_allowed > 0:
                result["warning"] = True
                result["remaining"] = max(0, max_allowed - new_count)
