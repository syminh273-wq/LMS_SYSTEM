from core.services.base_service import BaseService
from ..repositories.voice_setting_repository import UserVoiceSettingRepository
from ..constants import UserTypes

class UserVoiceSettingService(BaseService):
    repository = UserVoiceSettingRepository()

    def get_or_create_default(self, user_id, user_type):
        setting = self.repository.get_by_user(user_id)
        if not setting:
            setting = self.repository.create(
                user_id=user_id,
                user_type=user_type
            )
        return setting

    def update_settings(self, user_id, user_type, **data):
        setting = self.get_or_create_default(user_id, user_type)
        return self.repository.update(setting, **data)
