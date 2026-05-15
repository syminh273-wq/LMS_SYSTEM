from core.notification.enums.notification_provider import NotificationProvider
from core.firebase.realtime.realtime_service import RealtimeFirebaseService
from core.firebase.fcm.fcm_service import FCMFirebaseService


class NotificationService:
    def __init__(self, provider: str):
        self._client = self._init_client(provider)

    def _init_client(self, provider: str):
        if provider == NotificationProvider.REALTIME_DB.value:
            return RealtimeFirebaseService()
        if provider == NotificationProvider.FCM.value:
            return FCMFirebaseService()
        raise ValueError(f"Unsupported notification provider: {provider}")

    def set_message(self, channel: str, data: dict) -> bool:
        return self._client.set_message(channel, data)

    def push_message(self, channel: str, data: dict):
        return self._client.push_message(channel, data)

    def get_message(self, channel: str):
        return self._client.get_message(channel)

    def send_notification(self, target: str, payload, mode: str = "token"):
        if not hasattr(self._client, "send_notification"):
            raise NotImplementedError("send_notification is not supported by this provider")
        return self._client.send_notification(target, payload, mode)
