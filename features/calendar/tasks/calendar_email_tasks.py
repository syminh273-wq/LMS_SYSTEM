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


def enqueue_recurring_email(
    classroom_uid,
    event_uids,
    start_date,
    end_date,
    title,
    event_type,
    description,
):
    """Enqueue background job to send a single summary email for a recurring schedule."""
    description_value = description if description is not None else ""
    try:
        queue = django_rq.get_queue("default")
        queue.enqueue(
            _send_recurring_email_job,
            args=(
                str(classroom_uid),
                [str(uid) for uid in event_uids],
                start_date,
                end_date,
                title,
                event_type,
                description_value,
            ),
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


def _send_recurring_email_job(
    classroom_uid,
    event_uids,
    start_date,
    end_date,
    title,
    event_type,
    description="",
):
    from features.calendar.services.calendar_notification_service import CalendarNotificationService

    try:
        result = CalendarNotificationService().send_recurring_schedule_notification(
            classroom_uid=classroom_uid,
            event_uids=event_uids,
            start_date=start_date,
            end_date=end_date,
            title=title,
            event_type=event_type,
            description=description or "",
        )
        logger.info("[CalendarEmail] Recurring %s email result: %s", classroom_uid, result)
    except Exception as exc:
        logger.exception("[CalendarEmail] Recurring %s email failed: %s", classroom_uid, exc)
