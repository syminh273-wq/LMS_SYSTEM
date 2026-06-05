from core.repositories.base_repository import BaseRepository
from ..models.user_setting import UserSetting

class UserSettingRepository(BaseRepository):
    model = UserSetting

    def get_by_key(self, user_id, key):
        """Retrieve a specific setting for a user."""
        return self._qs().filter(bucket=0, user_id=user_id, key=key).first()

    def get_all_for_user(self, user_id):
        """Retrieve all settings for a user."""
        return self._qs().filter(bucket=0, user_id=user_id).all()

    def set_value(self, user_id, user_type, key, value):
        """Create or update a setting."""
        instance = self.get_by_key(user_id, key)
        if instance:
            return self.update(instance, value=str(value))
        return self.create(
            user_id=user_id,
            user_type=user_type,
            key=key,
            value=str(value)
        )
