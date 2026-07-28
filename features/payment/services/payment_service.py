import base64
import json
import logging
from datetime import datetime, timezone
from core.utils.uuid import uuid7
from features.payment.enums import PaymentStatus
from features.payment.repositories import PaymentRepository
from features.payment.services.momo_service import MoMoService
from core.services.base_service import BaseService

logger = logging.getLogger(__name__)

PENDING_TTL_SECONDS = 15 * 60


class PaymentService(BaseService):
    def __init__(self):
        self.repo = PaymentRepository()
        self.momo = MoMoService()

    def initiate(self, consumer_id, amount: int, order_info: str, resource_type: str, resource_id: str) -> dict:
        existing = self.repo.find_existing_for_resource(
            consumer_id=consumer_id,
            resource_type=resource_type,
            resource_id=str(resource_id),
        )
        if existing:
            if existing.status == PaymentStatus.COMPLETED.value:
                return self._reuse_response(existing, status='completed')
            if existing.status == PaymentStatus.PENDING.value:
                created = getattr(existing, 'created_at', None)
                age = (datetime.now(timezone.utc) - created).total_seconds() if created else 0
                if age < PENDING_TTL_SECONDS:
                    return self._reuse_response(existing, status='pending')

        order_id = str(uuid7())

        teacher_id = None
        if resource_type == 'classroom':
            try:
                from features.course.classroom.repositories import Repository
                classroom = Repository().find(str(resource_id))
                teacher_id = str(getattr(classroom, 'teacher_id', '')) or None
            except Exception:
                teacher_id = None
        elif resource_type == 'course':
            try:
                from features.course.repositories import CourseRepository
                course = CourseRepository().find(str(resource_id))
                teacher_id = str(getattr(course, 'teacher_id', '') or getattr(course, 'space_id', '') or '') or None
            except Exception:
                teacher_id = None

        meta = {
            "consumer_id": str(consumer_id),
            "resource_type": resource_type,
            "resource_id": str(resource_id),
        }
        if teacher_id:
            meta["teacher_id"] = teacher_id
        extra_data = base64.b64encode(json.dumps(meta).encode()).decode()

        result = self.momo.create_payment(
            order_id=order_id,
            amount=amount,
            order_info=order_info,
            extra_data=extra_data,
        )

        if result.get('resultCode') != 0:
            raise ValueError(result.get('message', 'MoMo payment creation failed'))

        self.repo.create(
            consumer_id=consumer_id,
            teacher_id=teacher_id,
            order_id=order_id,
            request_id=result.get('request_id', ''),
            amount=amount,
            order_info=order_info,
            extra_data=extra_data,
            status=PaymentStatus.PENDING.value,
            pay_url=result.get('payUrl', ''),
        )

        return {
            "order_id": order_id,
            "pay_url": result.get('payUrl', ''),
            "deeplink": result.get('deeplink', ''),
            "qr_code_url": result.get('qrCodeUrl', ''),
            "status": PaymentStatus.PENDING.value,
        }

    def _reuse_response(self, payment, status: str) -> dict:
        return {
            "order_id": payment.order_id,
            "pay_url": payment.pay_url or '',
            "deeplink": '',
            "qr_code_url": '',
            "status": status,
        }

    def handle_ipn(self, data: dict) -> None:
        if not self.momo.verify_ipn(data):
            raise PermissionError('Invalid MoMo IPN signature')

        order_id = data.get('orderId')
        result_code = int(data.get('resultCode', -1))
        trans_id = int(data.get('transId', 0))

        payment = self.repo.get_by_order_id(order_id)
        if not payment:
            logger.warning(f'[Payment] IPN received for unknown order: {order_id}')
            return

        if payment.status != PaymentStatus.PENDING.value:
            return

        if result_code == 0:
            payment.update(status=PaymentStatus.COMPLETED.value, result_code=result_code, trans_id=trans_id)
            self._on_payment_success(payment)
        else:
            payment.update(status=PaymentStatus.FAILED.value, result_code=result_code, trans_id=trans_id)

    def _on_payment_success(self, payment) -> None:
        try:
            meta = json.loads(base64.b64decode(payment.extra_data).decode())
            resource_type = meta.get('resource_type')
            resource_id = meta.get('resource_id')
            consumer_id = meta.get('consumer_id')

            if resource_type == 'classroom':
                from features.course.classroom.services.classroom_member_service import ClassroomMemberService
                ClassroomMemberService().approve_paid_member(resource_id, consumer_id)
        except Exception as e:
            logger.error(f'[Payment] Post-payment action failed for order {payment.order_id}: {e}')
