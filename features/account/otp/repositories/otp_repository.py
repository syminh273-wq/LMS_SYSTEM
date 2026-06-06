from uuid import UUID
from features.account.otp.models import OTPRecord


class OTPRepository:

    def upsert(self, user_uid: UUID, user_type: str, **kwargs) -> OTPRecord:
        existing = OTPRecord.objects.filter(user_uid=user_uid, user_type=user_type).first()
        if existing:
            existing.update(**kwargs)
            for k, v in kwargs.items():
                setattr(existing, k, v)
            return existing
        return OTPRecord.objects.create(user_uid=user_uid, user_type=user_type, **kwargs)

    def get_by_user(self, user_uid: UUID, user_type: str):
        return OTPRecord.objects.filter(user_uid=user_uid, user_type=user_type).first()

    def get_by_reset_token(self, reset_token: UUID):
        return OTPRecord.objects.filter(reset_token=reset_token).first()

    def save(self, instance: OTPRecord) -> OTPRecord:
        instance.save()
        return instance
