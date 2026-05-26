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


class EmailNotificationInterface(abc.ABC):
    """Interface for Email notification operations."""

    @abc.abstractmethod
    def send_mail(self, subject: str, message: str, recipient_list: list, html_message: str = None):
        """Send an email to a list of recipients."""

    @abc.abstractmethod
    def send_template_mail(self, subject: str, template_name: str, context: dict, recipient_list: list):
        """Send an email using a template."""

    @abc.abstractmethod
    def send_token_template(self, recipient_list: list, token: str, template_name: str = None):
        """Send a token using a template (defaults to token_template.html)."""
