from core.notification.enums.notification_provider import NotificationProvider
from core.firebase.realtime.realtime_service import RealtimeFirebaseService
from core.firebase.fcm.fcm_service import FCMFirebaseService
from core.notification.services.mail_service import MailService


class NotificationService:
    def __init__(self, provider: str):
        self._client = self._init_client(provider)

    def _init_client(self, provider: str):
        if provider == NotificationProvider.REALTIME_DB.value:
            return RealtimeFirebaseService()
        if provider == NotificationProvider.FCM.value:
            return FCMFirebaseService()
        if provider == NotificationProvider.EMAIL.value:
            return MailService()
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

    def send_mail(self, subject: str, message: str, recipient_list: list, html_message: str = None):
        if not hasattr(self._client, "send_mail"):
            raise NotImplementedError("send_mail is not supported by this provider")
        return self._client.send_mail(subject, message, recipient_list, html_message)

    def send_template_mail(self, subject: str, template_name: str, context: dict, recipient_list: list):
        if not hasattr(self._client, "send_template_mail"):
            raise NotImplementedError("send_template_mail is not supported by this provider")
        return self._client.send_template_mail(subject, template_name, context, recipient_list)

    def send_token_template(self, recipient_list: list, token: str, template_name: str = None):
        if not hasattr(self._client, "send_token_template"):
            raise NotImplementedError("send_token_template is not supported by this provider")
        return self._client.send_token_template(recipient_list, token, template_name)
