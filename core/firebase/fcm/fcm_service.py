import json
import logging

from firebase_admin import messaging

from core.firebase.client.firebase_app import FirebaseApp
from core.notification.dto.notification_dto import NotificationPayloadDto
from core.notification.interfaces.notification_interface import PushNotificationInterface

logger = logging.getLogger(__name__)


class FCMFirebaseService(PushNotificationInterface):

    def send_notification(self, target: str, payload: NotificationPayloadDto, mode: str = "token"):
        try:
            message_args = {
                "data": {
                    "event": str(payload.event),
                    "action": str(payload.action),
                    "sub_action": str(payload.sub_action),
                    "trigger": json.dumps(payload.trigger),
                },
            }

            if payload.title or payload.body:
                message_args["notification"] = messaging.Notification(
                    title=payload.title,
                    body=payload.body,
                )

            if mode == "token":
                message_args["token"] = target
            elif mode == "topic":
                message_args["topic"] = target
            elif mode == "condition":
                message_args["condition"] = target
            else:
                raise ValueError(f"Unsupported FCM mode: {mode}")

            message = messaging.Message(**message_args)
            return FirebaseApp.send_fcm(message)

        except Exception as e:
            logger.error(f"[FCM] send_notification failed: {e}")
            return None
