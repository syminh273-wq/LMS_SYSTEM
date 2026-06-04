from core.repositories.base_repository import BaseRepository
from ..models.voice_setting import UserVoiceSetting

class UserVoiceSettingRepository(BaseRepository):
    model = UserVoiceSetting

    def get_by_user(self, user_id):
        return self._qs().filter(bucket=0, user_id=user_id).first()
