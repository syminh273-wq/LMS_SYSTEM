import logging
from datetime import datetime
from typing import List, Optional

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.notification.services.mail_service import MailService
from features.account.consumer.models import Consumer
from features.account.consumer.repositories import ConsumerRepository
from features.calendar.repositories.calendar_event_repository import CalendarEventRepository
from features.course.classroom.models.classroom import Classroom
from features.course.classroom.repositories.classroom_repository import ClassroomRepository
from core.services.base_service import BaseService
from features.course.classroom.services.classroom_member_service import ClassroomMemberService

logger = logging.getLogger(__name__)


TYPE_LABELS_VI = {
    "class": "Buổi học",
    "exam": "Lịch thi",
    "deadline": "Hạn nộp",
    "study_session": "Tự học",
}

TYPE_SUBJECT_PREFIX = {
    "class": "[LMS] Lịch học",
    "exam": "[LMS] Lịch thi",
    "deadline": "[LMS] Hạn nộp",
    "study_session": "[LMS] Lịch tự học",
}


def _resolve_classroom_name(classroom: Optional[Classroom]) -> str:
    if classroom is None:
        return ""
    try:
        return classroom.name or ""
    except Exception:
        return ""


def _classroom_consumer_recipients(classroom_uid) -> List[dict]:
    try:
        members = ClassroomMemberService().get_members(classroom_uid)
    except Exception as exc:
        logger.warning("[CalendarEmail] Failed to load members for %s: %s", classroom_uid, exc)
        return []

    consumer_repo = ConsumerRepository()
    recipients: List[dict] = []
    for m in members:
        try:
            consumer: Consumer = consumer_repo.find(m.member_id)
        except Exception:
            continue
        email = (getattr(consumer, "email", "") or "").strip()
        if not email:
            continue
        name = (getattr(consumer, "full_name", "") or "").strip() or email
        recipients.append({"name": name, "email": email})
    return recipients


def _frontend_event_url(event_uid: str) -> str:
    base = getattr(settings, "FRONTEND_CONSUMER_URL", "http://localhost:3000")
    return f"{base.rstrip('/')}/consumer/calendar?event={event_uid}"


def _frontend_classroom_url(classroom_uid: str) -> str:
    base = getattr(settings, "FRONTEND_CONSUMER_URL", "http://localhost:3000")
    return f"{base.rstrip('/')}/consumer/classroom/{classroom_uid}"


class CalendarNotificationService(BaseService):
    def __init__(self):
        self.event_repo = CalendarEventRepository()
        self.classroom_repo = ClassroomRepository()
        self.mail = MailService()

    def send_event_notification(self, event_uid) -> dict:
        try:
            event = self.event_repo.find(event_uid)
        except Exception as exc:
            logger.warning("[CalendarEmail] Event %s not found: %s", event_uid, exc)
            return {"sent": 0, "skipped": True, "reason": "event_not_found"}

        if not event.classroom_id:
            return {"sent": 0, "skipped": True, "reason": "no_classroom"}

        classroom = self._safe_find_classroom(event.classroom_id)
        emails = [r["email"] for r in _classroom_consumer_recipients(event.classroom_id)]
        if not emails:
            return {"sent": 0, "skipped": True, "reason": "no_recipients"}

        event_type = event.type or "class"
        type_label = TYPE_LABELS_VI.get(event_type, event_type)
        prefix = TYPE_SUBJECT_PREFIX.get(event_type, "[LMS] Lịch học")
        subject = f"{prefix} - {event.title}"

        context = {
            "title": event.title,
            "event_type": event_type,
            "type_label": type_label,
            "classroom_name": _resolve_classroom_name(classroom) or "—",
            "start_time": _fmt_dt(event.start_time),
            "end_time": _fmt_dt(event.end_time),
            "description": event.description or "",
            "action_url": _frontend_event_url(str(event.uid)),
            "action_text": "Xem chi tiết",
        }
        return self._send(emails, subject, "emails/calendar_event_notification.html", context)

    def send_recurring_schedule_notification(self, classroom_uid) -> dict:
        recipients = _classroom_consumer_recipients(classroom_uid)
        if not recipients:
            return {"sent": 0, "skipped": True, "reason": "no_recipients"}

        classroom = self._safe_find_classroom(classroom_uid)
        classroom_name = _resolve_classroom_name(classroom) or "—"
        classroom_url = _frontend_classroom_url(str(classroom_uid))
        system_name = getattr(settings, "SITE_NAME", "LMS System")
        subject = f'[LMS] You have been added to "{classroom_name}"'

        sent = 0
        for recipient in recipients:
            context = {
                "student_name": recipient["name"],
                "classroom_name": classroom_name,
                "classroom_url": classroom_url,
                "system_name": system_name,
            }
            result = self._send([recipient["email"]], subject, "emails/calendar_recurring_schedule.html", context)
            sent += result.get("sent", 0)

        return {"sent": sent, "skipped": False, "recipients": len(recipients)}

    def _safe_find_classroom(self, classroom_uid) -> Optional[Classroom]:
        try:
            return self.classroom_repo.find(classroom_uid)
        except Exception:
            return None

    def _send(self, recipients: List[str], subject: str, template: str, context: dict) -> dict:
        logger.info(
            "[CalendarEmail] Sending '%s' to %d recipient(s): %s",
            subject,
            len(recipients),
            recipients,
        )
        try:
            html_message = render_to_string(template, context)
            plain_message = strip_tags(html_message)
            self.mail.send_mail(
                subject=subject,
                message=plain_message,
                recipient_list=recipients,
                html_message=html_message,
            )
            logger.info(
                "[CalendarEmail] Sent '%s' successfully to %s", subject, recipients
            )
            return {"sent": len(recipients), "skipped": False}
        except Exception as exc:
            logger.exception("[CalendarEmail] Failed to send mail: %s", exc)
            return {"sent": 0, "skipped": False, "error": str(exc)}


def _fmt_dt(dt: datetime) -> str:
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)
