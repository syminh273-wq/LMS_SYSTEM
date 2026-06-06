import random
import string
from datetime import datetime, timedelta
from uuid import uuid4

from rest_framework import exceptions

from core.notification.services.mail_service import MailService
from features.account.otp.repositories import OTPRepository


def _generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))


class OTPService:
    def __init__(self):
        self.repository = OTPRepository()
        self.mail_service = MailService()

    def _get_user(self, email: str, user_type: str):
        if user_type == 'consumer':
            from features.account.consumer.repositories import ConsumerRepository
            try:
                return ConsumerRepository().get_by_email(email)
            except Exception:
                return None
        elif user_type == 'space':
            from features.account.space.repositories import Repository as SpaceRepository
            try:
                return SpaceRepository().get_by_email(email)
            except Exception:
                return None
        return None

    def request_otp(self, email: str, user_type: str):
        user = self._get_user(email, user_type)
        if user is None:
            # Return success regardless to avoid email enumeration
            return {'message': 'Nếu email tồn tại, mã OTP đã được gửi.'}

        otp_code = _generate_otp()
        expires_at = datetime.now() + timedelta(minutes=5)

        self.repository.upsert(
            user_uid=user.uid,
            user_type=user_type,
            otp_code=otp_code,
            email=email,
            expires_at=expires_at,
            reset_token=None,
            reset_expires_at=None,
            is_otp_verified=False,
            is_reset_used=False,
        )

        self.mail_service.send_token_template(
            recipient_list=[email],
            token=otp_code,
        )

        return {'message': 'Nếu email tồn tại, mã OTP đã được gửi.'}

    def verify_otp(self, email: str, user_type: str, otp_code: str):
        user = self._get_user(email, user_type)
        if user is None:
            raise exceptions.ValidationError({'detail': 'Email hoặc mã OTP không hợp lệ.'})

        record = self.repository.get_by_user(user.uid, user_type)
        if record is None:
            raise exceptions.ValidationError({'detail': 'Không tìm thấy yêu cầu đặt lại mật khẩu.'})

        if record.is_otp_verified:
            raise exceptions.ValidationError({'detail': 'Mã OTP đã được sử dụng.'})

        if datetime.now() > record.expires_at:
            raise exceptions.ValidationError({'detail': 'Mã OTP đã hết hạn. Vui lòng yêu cầu mã mới.'})

        if record.otp_code != otp_code:
            raise exceptions.ValidationError({'otp_code': ['Mã OTP không chính xác.']})

        reset_token = uuid4()
        reset_expires_at = datetime.now() + timedelta(minutes=10)

        record.update(
            is_otp_verified=True,
            reset_token=reset_token,
            reset_expires_at=reset_expires_at,
        )

        return {'reset_token': str(reset_token)}

    def reset_password(self, reset_token: str, new_password: str, user_type: str):
        from uuid import UUID
        try:
            token_uuid = UUID(reset_token)
        except (ValueError, AttributeError):
            raise exceptions.ValidationError({'detail': 'Token không hợp lệ.'})

        record = self.repository.get_by_reset_token(token_uuid)
        if record is None:
            raise exceptions.ValidationError({'detail': 'Token không hợp lệ hoặc đã hết hạn.'})

        if not record.is_otp_verified:
            raise exceptions.ValidationError({'detail': 'OTP chưa được xác thực.'})

        if record.is_reset_used:
            raise exceptions.ValidationError({'detail': 'Token này đã được sử dụng.'})

        if record.user_type != user_type:
            raise exceptions.ValidationError({'detail': 'Token không hợp lệ.'})

        if datetime.now() > record.reset_expires_at:
            raise exceptions.ValidationError({'detail': 'Token đã hết hạn. Vui lòng thực hiện lại từ đầu.'})

        user = self._get_user(record.email, user_type)
        if user is None:
            raise exceptions.ValidationError({'detail': 'Người dùng không tồn tại.'})

        user.set_password(new_password)
        user.save()

        record.update(is_reset_used=True)

        return {'message': 'Mật khẩu đã được cập nhật thành công.'}
