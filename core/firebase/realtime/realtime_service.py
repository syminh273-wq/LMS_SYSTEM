from core.firebase.client.firebase_app import FirebaseApp
from core.notification.services.base_realtime_service import BaseRealtimeService


class RealtimeFirebaseService(BaseRealtimeService):

    def _set_value(self, channel: str, data):
        FirebaseApp.set_value(channel, data)

    def _push_value(self, channel: str, data):
        return FirebaseApp.push_value(channel, data)

    def _get_value(self, channel: str):
        return FirebaseApp.get_value(channel)
