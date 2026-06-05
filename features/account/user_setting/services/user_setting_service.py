from core.services.base_service import BaseService
from ..repositories.user_setting_repository import UserSettingRepository

class UserSettingService(BaseService):
    repository = UserSettingRepository()

    def get_all_settings(self, user_id):
        """Get all settings as a dictionary."""
        settings = self.repository.get_all_for_user(user_id)
        return {s.key: s.value for s in settings}

    def get_setting(self, user_id, key, default=None):
        """Get a specific setting value."""
        instance = self.repository.get_by_key(user_id, key)
        return instance.value if instance else default

    def set_setting(self, user_id, user_type, key, value):
        """Set a single setting."""
        return self.repository.set_value(user_id, user_type, key, value)

    def update_bulk_settings(self, user_id, user_type, settings_dict: dict):
        """Update multiple settings."""
        results = []
        for key, value in settings_dict.items():
            results.append(self.set_setting(user_id, user_type, key, value))
        return results
