import json
import uuid
from features.notification.models.notification_log import NotificationLog
from core.notification.services.notification_service import NotificationService as FirebaseNotificationService
from core.notification.enums.notification_provider import NotificationProvider
from core.firebase.client.firebase_app import FirebaseApp

class NotificationService:
    def __init__(self):
        self.firebase_service = FirebaseNotificationService(provider=NotificationProvider.REALTIME_DB.value)

    def send_notification(self, target_uid, notify_type, title, content, metadata=None):
        """
        1. Save to Cassandra
        2. Push to Firebase
        """
        # Save to DB
        log = NotificationLog.create(
            target_uid=uuid.UUID(str(target_uid)),
            notify_type=notify_type,
            title=title,
            content=content,
            metadata=json.dumps(metadata) if metadata else None
        )

        # Push to Firebase using notification uid as key so is_read can be updated later
        # Path: notifications/{target_uid}/{notification_uid}
        channel = f"notifications/{target_uid}/{log.uid}"
        firebase_data = {
            "uid": str(log.uid),
            "type": notify_type,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "is_read": "false",
            "created_at": log.created_at.isoformat()
        }
        self.firebase_service.set_message(channel, firebase_data)

        return log

    def get_user_notifications(self, target_uid, limit=20):
        return NotificationLog.objects.filter(target_uid=uuid.UUID(str(target_uid))).limit(limit)

    def get_all_notifications(self, limit=50):
        # Querying all in Cassandra might require ALLOW FILTERING if not careful, 
        # but basic objects.all().limit() works for global logs.
        return NotificationLog.objects.all().limit(limit)

    def mark_as_read(self, target_uid, notification_uid):
        log = NotificationLog.objects.filter(
            target_uid=uuid.UUID(str(target_uid)),
            uid=uuid.UUID(str(notification_uid))
        ).first()
        if log:
            log.update(is_read=True)
            FirebaseApp.update_value(
                f"notifications/{target_uid}/{notification_uid}",
                {"is_read": "true"}
            )
        return log

    def mark_all_as_read(self, target_uid):
        import logging
        logger = logging.getLogger(__name__)

        target_uuid = uuid.UUID(str(target_uid))
        logger.info(f"[Notification] Mark all as read for target_uid: {target_uuid}")

        notifications = NotificationLog.objects.filter(
            target_uid=target_uuid
        ).all()

        notif_list = list(notifications)
        logger.info(f"[Notification] Found {len(notif_list)} notifications total for this target")

        count = 0
        for notif in notif_list:
            if not notif.is_read:
                notif.update(is_read=True)
                FirebaseApp.update_value(
                    f"notifications/{target_uid}/{notif.uid}",
                    {"is_read": "true"}
                )
                count += 1

        logger.info(f"[Notification] Updated {count} notifications to is_read=True")
        return count
