import abc

from core.notification.dto.notification_dto import NotificationPayloadDto


class RealtimeInterface(abc.ABC):
    """Interface for Firebase Realtime Database pub/sub operations."""

    @abc.abstractmethod
    def set_message(self, channel: str, data: dict) -> bool:
        """Overwrite data at a channel path."""

    @abc.abstractmethod
    def push_message(self, channel: str, data: dict):
        """Append a new child entry to a channel (list push)."""

    @abc.abstractmethod
    def get_message(self, channel: str):
        """Read current value at a channel path."""


class PushNotificationInterface(abc.ABC):
    """Interface for FCM push notification operations."""

    @abc.abstractmethod
    def send_notification(self, target: str, payload: NotificationPayloadDto, mode: str = "token"):
        """Send a push notification to a device token, topic, or condition."""
