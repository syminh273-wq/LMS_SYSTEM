import json
import logging
from datetime import datetime

from features.course.exam.repositories import (
    ExamAuditLogRepository,
    ExamRepository,
    ExamSessionRepository,
)

logger = logging.getLogger(__name__)


def _safe_uuid(value):
    try:
        from uuid import UUID
        return UUID(str(value))
    except Exception:
        return None


def _humanize_event(event_type: str) -> str:
    mapping = {
        "tab_leave":            "Bạn vừa rời khỏi tab bài thi. Hãy quay lại ngay nhé.",
        "tab_return":           "Bạn đã quay lại tab bài thi. Cố gắng giữ tập trung nhé!",
        "window_out":           "Bạn vừa chuyển sang cửa sổ khác. Hãy quay lại bài thi.",
        "window_back":          "Chào mừng bạn quay lại. Mình tiếp tục làm bài nhé!",
        "window_blur":          "Cửa sổ bài thi vừa mất focus — bạn nhớ không chuyển tab nhé.",
        "app_blur":             "Bài thi vừa bị ẩn. Hãy quay lại ngay để tránh bị tính lỗi.",
        "app_focus":            "Tuyệt, bạn đã quay lại bài thi rồi!",
        "fullscreen_exit":      "Bạn vừa thoát chế độ toàn màn hình. Hãy bật lại để tiếp tục.",
        "visibility_lost":      "Trang bài thi vừa bị ẩn. Hãy mở lại ngay nhé.",
        "visibility_restored":  "Bài thi đã hiển thị lại. Bạn làm tốt lắm!",
        "camera_lost":          "Mình không thấy camera. Bạn kiểm tra lại camera giúp mình nhé.",
        "face_not_recognized":  "Chưa nhận diện được khuôn mặt. Bạn ngồi thẳng, nhìn thẳng camera và đảm bảo đủ ánh sáng nhé.",
        "no_face":              "Chưa thấy bạn trong khung hình. Bạn ngồi lại trước camera giúp mình nhé.",
        "multiple_faces":       "Có nhiều người trong khung hình. Bạn đảm bảo chỉ mình bạn trong phòng thi nhé.",
        "joined":               "Chào bạn! Chúc bạn làm bài thật tốt.",
        "submitted":            "Bạn đã nộp bài thành công.",
        "timeout_submit":       "Đã hết giờ làm bài. Hệ thống đã tự động nộp bài giúp bạn.",
        "force_submitted":      "Bài thi đã được hệ thống nộp bắt buộc do bạn vi phạm quy chế. Giáo viên sẽ xem xét bài làm của bạn.",
        "visibility_breaks_exceeded":   "Bạn đã rời màn hình quá nhiều lần. Hệ thống sẽ nộp bài bắt buộc và báo cáo giáo viên.",
        "face_warnings_exceeded":       "Bạn đã vi phạm quy chế camera quá nhiều lần. Hệ thống sẽ nộp bài bắt buộc và báo cáo giáo viên.",
    }
    return mapping.get(event_type, f"Sự kiện: {event_type}")


class ExamAuditEventService:
    """
    Ghi và xử lý các sự kiện giám sát trong phòng thi online.

    Quy tắc:
      - Nhóm 1 (visibility): gộp tất cả các hành vi rời khỏi bài thi
        (tab_leave, window_out, window_blur, app_blur, fullscreen_exit,
        visibility_lost) vào 1 counter duy nhất `visibility_breaks_count`,
        giới hạn bởi `max_visibility_breaks` của Exam.
      - Nhóm 2 (face): các cảnh báo camera/khuôn mặt
        (camera_lost, face_not_recognized, multiple_faces) đếm riêng
        vào `face_warnings_count`, giới hạn bởi `max_face_warnings`.
      - Mỗi lần vi phạm đều trả `warning=True` cùng `severity` và `message`
        để frontend hiển thị cảnh báo cho học sinh ngay lập tức.
      - Khi vượt max → force_submit (điểm vẫn tính, is_effective=False).
    """

    VISIBILITY_BREAK_EVENTS = {
        "tab_leave",
        "window_out",
        "window_blur",
        "app_blur",
        "fullscreen_exit",
        "visibility_lost",
    }
    VISIBILITY_RETURN_EVENTS = {
        "tab_return",
        "window_back",
        "app_focus",
        "visibility_restored",
    }
    FACE_WARNING_EVENTS = {
        "camera_lost",
        "face_not_recognized",
        "no_face",
        "multiple_faces",
    }

    def __init__(self):
        self.session_repo = ExamSessionRepository()
        self.exam_repo = ExamRepository()
        self.audit_repo = ExamAuditLogRepository()

    def record_event(self, session_uid, student_id, event_type, event_data=None):
        """
        Trả về dict:
          {
            "logged": True,
            "warning": bool,           # luôn True nếu event thuộc nhóm vi phạm
            "severity": "info" | "warning" | "danger",
            "message": str,            # text thân thiện hiển thị cho SV
            "event_type": str,
            "count": int,              # counter hiện tại
            "max": int,                # max tương ứng (0 = unlimited)
            "remaining": int | None,   # lượt còn lại (None nếu unlimited)
            "rule": "visibility_breaks" | "face_warnings" | None,
            "force_submitted": bool,
            "submission": {...} | None,
          }
        """
        event_data = event_data if isinstance(event_data, dict) else {}

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

        is_visibility_break  = event_type in self.VISIBILITY_BREAK_EVENTS
        is_visibility_return = event_type in self.VISIBILITY_RETURN_EVENTS
        is_face_warning      = event_type in self.FACE_WARNING_EVENTS
        is_informational     = (
            event_type in {"joined", "submitted", "timeout_submit", "force_submitted"}
            or is_visibility_return
        )

        result = {
            "logged": True,
            "warning": False,
            "severity": "info",
            "message": _humanize_event(event_type),
            "event_type": event_type,
            "count": 0,
            "max": 0,
            "remaining": None,
            "force_submitted": False,
            "submission": None,
            "rule": None,
        }

        if is_visibility_break:
            result["rule"] = "visibility_breaks"
            result["max"] = int(getattr(exam, "max_visibility_breaks", 0) or 0)
        elif is_face_warning:
            result["rule"] = "face_warnings"
            result["max"] = int(getattr(exam, "max_face_warnings", 0) or 0)

        try:
            self.audit_repo.log(
                exam_id=exam.uid,
                student_id=student_id,
                event_type=event_type,
                event_data=event_data,
            )
        except Exception as exc:
            logger.exception("ExamAuditEventService: log raw event failed: %s", exc)
            result["logged"] = False
            result["message"] = "Không thể ghi log sự kiện. Vui lòng thử lại."
            return result

        try:
            self.session_repo.update(session, last_event_at=now)
        except Exception as exc:
            logger.exception("ExamAuditEventService: update last_event_at failed: %s", exc)
        session = self.session_repo.get_by_uid(session_uid) or session

        if is_visibility_break:
            self._increment_and_check(
                session=session,
                exam=exam,
                student_id=student_id,
                rule="visibility_breaks",
                event_type=event_type,
                payload=event_data,
                now=now,
                current_count=int(getattr(session, "visibility_breaks_count", 0) or 0),
                counter_field="visibility_breaks_count",
                exceeded_event="visibility_breaks_exceeded",
                result=result,
            )
        elif is_face_warning:
            self._increment_and_check(
                session=session,
                exam=exam,
                student_id=student_id,
                rule="face_warnings",
                event_type=event_type,
                payload=event_data,
                now=now,
                current_count=int(getattr(session, "face_warnings_count", 0) or 0),
                counter_field="face_warnings_count",
                exceeded_event="face_warnings_exceeded",
                result=result,
            )
        else:
            result["warning"] = is_informational is False
            result["severity"] = "info"

        return result

    def _increment_and_check(
        self,
        session,
        exam,
        student_id,
        rule,
        event_type,
        payload,
        now,
        current_count,
        counter_field,
        exceeded_event,
        result,
    ):
        """Tăng counter, set severity, ghi log limit-exceeded, force_submit khi vượt max."""
        new_count = current_count + 1
        try:
            self.session_repo.update(
                session,
                **{counter_field: new_count},
                last_event_at=now,
            )
            session = self.session_repo.get_by_uid(session.uid) or session
        except Exception as exc:
            logger.exception(
                "ExamAuditEventService: increment %s failed: %s", counter_field, exc
            )

        result["count"] = new_count
        max_allowed = result["max"]

        if max_allowed > 0:
            result["remaining"] = max(0, max_allowed - new_count)
            if new_count > max_allowed:
                result["severity"] = "danger"
            elif new_count >= max(1, max_allowed - 1):
                result["severity"] = "warning"
            else:
                result["severity"] = "warning"
        else:
            result["severity"] = "warning"
            result["remaining"] = None

        result["warning"] = True

        if max_allowed > 0 and new_count > max_allowed:
            try:
                self.audit_repo.log(
                    exam_id=exam.uid,
                    student_id=student_id,
                    event_type=exceeded_event,
                    event_data={
                        "count": new_count,
                        "max": max_allowed,
                        "triggered_by": event_type,
                        "rule": rule,
                    },
                )
            except Exception as exc:
                logger.exception("ExamAuditEventService: log exceeded_event failed: %s", exc)

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
                    reason=exceeded_event,
                    data=submission_payload,
                )
                from features.course.exam.serializers import serialize_exam_submission
                result["submission"] = serialize_exam_submission(submission)
                result["force_submitted"] = True
                result["severity"] = "danger"
                result["message"] = _humanize_event(exceeded_event)

                try:
                    self.audit_repo.log(
                        exam_id=exam.uid,
                        student_id=student_id,
                        event_type="force_submitted",
                        event_data={
                            "reason": exceeded_event,
                            "count": new_count,
                            "max": max_allowed,
                            "rule": rule,
                            "submission_uid": str(submission.uid),
                        },
                    )
                except Exception as exc:
                    logger.exception("ExamAuditEventService: log force_submitted failed: %s", exc)
            except Exception as exc:
                logger.exception("force_submit failed: %s", exc)
