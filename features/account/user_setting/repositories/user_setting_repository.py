from core.repositories.base_repository import BaseRepository
from ..models.user_setting import UserSetting

class UserSettingRepository(BaseRepository):
    model = UserSetting

    def get_by_key(self, user_id, key):
        """Retrieve a specific setting for a user."""
        return self.filter(user_id=user_id, key=key, is_deleted=False).first()

    def get_all_for_user(self, user_id):
        """Retrieve all settings for a user."""
        return self.all().filter(user_id=user_id)

    def set_value(self, user_id, user_type, key, value):
        """Create or update a setting. `value` is expected to already be a string (JSON-encoded by the service)."""
        instance = self.get_by_key(user_id, key)
        if instance:
            return self.update(instance, value=value)
        return self.create(
            user_id=user_id,
            user_type=user_type,
            key=key,
            value=value
        )
