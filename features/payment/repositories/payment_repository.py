from core.repositories.base_repository import BaseRepository
from features.payment.models import Payment


class PaymentRepository(BaseRepository):
    model = Payment

    def get_by_order_id(self, order_id: str):
        return self.model.objects.filter(order_id=order_id).first()

    def get_by_consumer(self, consumer_id):
        return self.model.objects.filter(consumer_id=consumer_id, is_deleted=False)
