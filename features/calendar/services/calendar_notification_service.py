import logging
from datetime import datetime, timedelta, date as date_cls
from typing import Iterable, List, Optional

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.notification.services.mail_service import MailService
from features.account.consumer.models import Consumer
from features.account.consumer.repositories import ConsumerRepository
from features.calendar.models.calendar_event import CalendarEvent
from features.calendar.repositories.calendar_event_repository import CalendarEventRepository
from features.course.classroom.models.classroom import Classroom
from features.course.classroom.repositories.classroom_repository import Repository as ClassroomRepository
from features.course.classroom.services.classroom_member_service import ClassroomMemberService

logger = logging.getLogger(__name__)


SHIFTS = [
    {"id": 1, "label_vi": "Ca 1", "label_en": "Shift 1", "start": (7, 0), "end": (9, 0)},
    {"id": 2, "label_vi": "Ca 2", "label_en": "Shift 2", "start": (9, 30), "end": (11, 30)},
    {"id": 3, "label_vi": "Ca 3", "label_en": "Shift 3", "start": (13, 0), "end": (15, 0)},
    {"id": 4, "label_vi": "Ca 4", "label_en": "Shift 4", "start": (15, 30), "end": (17, 30)},
]

DAY_KEYS_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
DAY_DOW_ORDER = [1, 2, 3, 4, 5, 6, 0]

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


def _shift_for(dt: datetime) -> Optional[dict]:
    total = dt.hour * 60 + dt.minute
    for s in SHIFTS:
        s_start = s["start"][0] * 60 + s["start"][1]
        s_end = s["end"][0] * 60 + s["end"][1]
        if s_start <= total < s_end:
            return s
    return None


def _shift_label(s: dict) -> str:
    return s["label_vi"]


def _shift_time(s: dict) -> str:
    return f"{s['start'][0]:02d}:{s['start'][1]:02d} – {s['end'][0]:02d}:{s['end'][1]:02d}"


def _resolve_classroom_name(classroom: Optional[Classroom]) -> str:
    if classroom is None:
        return ""
    try:
        return classroom.name or ""
    except Exception:
        return ""


def _classroom_consumer_emails(classroom_uid) -> List[str]:
    try:
        members = ClassroomMemberService().get_members(classroom_uid)
    except Exception as exc:
        logger.warning("[CalendarEmail] Failed to load members for %s: %s", classroom_uid, exc)
        return []

    consumer_repo = ConsumerRepository()
    emails: List[str] = []
    for m in members:
        if getattr(m, "member_type", "consumer") != "consumer":
            continue
        if getattr(m, "role", "student") == "teacher":
            continue
        try:
            consumer: Consumer = consumer_repo.find(m.member_id)
        except Exception:
            continue
        email = (getattr(consumer, "email", "") or "").strip()
        if email:
            emails.append(email)
    return emails


def _frontend_event_url(event_uid: str) -> str:
    base = getattr(settings, "FRONTEND_CONSUMER_URL", "http://localhost:3000")
    return f"{base.rstrip('/')}/consumer/calendar?event={event_uid}"


def _frontend_classroom_url(classroom_uid: str) -> str:
    base = getattr(settings, "FRONTEND_CONSUMER_URL", "http://localhost:3000")
    return f"{base.rstrip('/')}/consumer/classroom/{classroom_uid}"


class CalendarNotificationService:
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
        emails = _classroom_consumer_emails(event.classroom_id)
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

    def send_recurring_schedule_notification(
        self,
        classroom_uid,
        event_uids: Iterable[str],
        start_date,
        end_date,
        title: str,
        event_type: str = "class",
        description: str = "",
    ) -> dict:
        emails = _classroom_consumer_emails(classroom_uid)
        if not emails:
            return {"sent": 0, "skipped": True, "reason": "no_recipients"}

        events: List[CalendarEvent] = []
        for uid in event_uids:
            try:
                events.append(self.event_repo.find(uid))
            except Exception as exc:
                logger.warning("[CalendarEmail] Skip event %s: %s", uid, exc)

        if not events:
            return {"sent": 0, "skipped": True, "reason": "no_events"}

        events.sort(key=lambda e: e.start_time)
        total_sessions = len(events)

        start = _parse_date(start_date)
        week1_start = start
        week1_end = start + timedelta(days=6) if start else None
        if week1_end:
            week1_events = [e for e in events if week1_start <= e.start_time.date() <= week1_end]
        else:
            week1_events = events
        week1_lines = [_format_event_line(e) for e in week1_events]

        classroom = self._safe_find_classroom(classroom_uid)
        type_label = TYPE_LABELS_VI.get(event_type, event_type)
        prefix = TYPE_SUBJECT_PREFIX.get(event_type, "[LMS] Lịch học")
        subject = f"{prefix} - {title} ({_fmt_date(start_date)} – {_fmt_date(end_date)})"

        context = {
            "title": title,
            "event_type": event_type,
            "type_label": type_label,
            "classroom_name": _resolve_classroom_name(classroom) or "—",
            "start_date": _fmt_date(start_date),
            "end_date": _fmt_date(end_date),
            "total_sessions": total_sessions,
            "week1_start": _fmt_date(week1_start) if week1_start else "",
            "week1_end": _fmt_date(week1_end) if week1_end else "",
            "week1_event_count": len(week1_events),
            "week1_event_lines": week1_lines,
            "description": description or "",
            "action_url": _frontend_classroom_url(str(classroom_uid)),
            "action_text": "Xem lịch đầy đủ",
        }
        return self._send(emails, subject, "emails/calendar_recurring_schedule.html", context)

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


def _weekday_match(dt: datetime, dow: int) -> bool:
    python_weekday = dt.weekday()
    return (dow - 1) % 7 == python_weekday


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_cls):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None
    return None


def _format_event_line(event: CalendarEvent) -> dict:
    shift = _shift_for(event.start_time)
    shift_label = _shift_label(shift) if shift else "Ngoài ca"
    shift_time = _shift_time(shift) if shift else f"{event.start_time.strftime('%H:%M')} – {event.end_time.strftime('%H:%M')}"
    py_weekday = event.start_time.weekday()
    day_label = DAY_KEYS_VI[py_weekday] if 0 <= py_weekday < 7 else ""
    return {
        "date_label": _fmt_date(event.start_time),
        "day_label": day_label,
        "shift_label": shift_label,
        "shift_time": shift_time,
        "title": event.title,
        "type": event.type or "class",
    }


def _fmt_dt(dt: datetime) -> str:
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


def _fmt_date(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date_cls):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y")
        except Exception:
            return value
    return str(value)
