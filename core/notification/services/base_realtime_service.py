import logging

from core.notification.interfaces.notification_interface import RealtimeInterface

logger = logging.getLogger(__name__)


class BaseRealtimeService(RealtimeInterface):

    def set_message(self, channel: str, data) -> bool:
        """Overwrite data at channel path. Pass None to delete."""
        try:
            if data is None:
                self._delete_value(channel)
            else:
                self._set_value(channel, self._to_string_values(data))
            return True
        except Exception as e:
            logger.error(f"[Realtime] set_message failed on {channel}: {e}")
            return False

    def push_message(self, channel: str, data: dict):
        """Append new child entry to channel (Firebase list push)."""
        try:
            return self._push_value(channel, self._to_string_values(data))
        except Exception as e:
            logger.error(f"[Realtime] push_message failed on {channel}: {e}")
            return None

    def get_message(self, channel: str):
        try:
            return self._get_value(channel)
        except Exception as e:
            logger.error(f"[Realtime] get_message failed on {channel}: {e}")
            return None

    def delete_message(self, channel: str) -> bool:
        try:
            self._delete_value(channel)
            return True
        except Exception as e:
            logger.error(f"[Realtime] delete_message failed on {channel}: {e}")
            return False

    def _to_string_values(self, data):
        if isinstance(data, dict):
            return {k: self._to_string_values(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._to_string_values(i) for i in data]
        return str(data)

    def _set_value(self, channel: str, data):
        raise NotImplementedError

    def _push_value(self, channel: str, data):
        raise NotImplementedError

    def _get_value(self, channel: str):
        raise NotImplementedError

    def _delete_value(self, channel: str):
        raise NotImplementedError
