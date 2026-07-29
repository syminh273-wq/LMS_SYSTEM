import logging
import uuid

import django_rq

logger = logging.getLogger(__name__)


def enqueue_event_email(event_uid):
    """Enqueue background job to send a single calendar-event email."""
    try:
        queue = django_rq.get_queue("default")
        queue.enqueue(
            _send_event_email_job,
            args=(str(event_uid),),
            job_id=f"calendar-event-email-{uuid.uuid4()}",
            job_timeout=120,
        )
    except Exception as exc:
        logger.warning("[CalendarEmail] Failed to enqueue event email: %s", exc)


def enqueue_recurring_email(classroom_uid):
    """Enqueue background job to notify classroom members about a new recurring schedule."""
    try:
        queue = django_rq.get_queue("default")
        queue.enqueue(
            _send_recurring_email_job,
            args=(str(classroom_uid),),
            job_id=f"calendar-recurring-email-{uuid.uuid4()}",
            job_timeout=180,
        )
    except Exception as exc:
        logger.warning("[CalendarEmail] Failed to enqueue recurring email: %s", exc)


def _send_event_email_job(event_uid):
    from features.calendar.services.calendar_notification_service import CalendarNotificationService

    try:
        result = CalendarNotificationService().send_event_notification(event_uid)
        logger.info("[CalendarEmail] Event %s email result: %s", event_uid, result)
    except Exception as exc:
        logger.exception("[CalendarEmail] Event %s email failed: %s", event_uid, exc)


def _send_recurring_email_job(classroom_uid):
    from features.calendar.services.calendar_notification_service import CalendarNotificationService

    try:
        result = CalendarNotificationService().send_recurring_schedule_notification(classroom_uid)
        logger.info("[CalendarEmail] Recurring %s email result: %s", classroom_uid, result)
    except Exception as exc:
        logger.exception("[CalendarEmail] Recurring %s email failed: %s", classroom_uid, exc)
