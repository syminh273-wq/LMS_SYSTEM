import json
import uuid
from datetime import datetime
from features.account.consumer.models.teacher_settings import TeacherSetting

class TeacherSettingsService:
    def get_all(self, teacher_uid):
        uid = uuid.UUID(str(teacher_uid))
        settings = TeacherSetting.objects.filter(teacher_uid=uid)
        result = {}
        for s in settings:
            try:
                result[s.key] = json.loads(s.value)
            except:
                result[s.key] = {}
        return result

    def update_bulk(self, teacher_uid, data: dict):
        uid = uuid.UUID(str(teacher_uid))
        now = datetime.utcnow()
        for key, value in data.items():
            value_str = json.dumps(value, ensure_ascii=False)
            try:
                # Upsert logic
                s = TeacherSetting.objects.get(teacher_uid=uid, key=key)
                s.value = value_str
                s.updated_at = now
                s.save()
            except TeacherSetting.DoesNotExist:
                TeacherSetting.create(
                    teacher_uid=uid,
                    key=key,
                    value=value_str,
                    updated_at=now
                )
        return self.get_all(teacher_uid)
