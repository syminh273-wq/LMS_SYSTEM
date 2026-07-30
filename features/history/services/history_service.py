from core.services.base_service import BaseService
from features.payment.repositories import PaymentRepository


class HistoryService(BaseService):
    def __init__(self):
        self.payments = PaymentRepository()

    def get_overview(self, consumer_id, limit: int = 50):
        limit = max(1, min(int(limit or 50), 200))
        payments = list(self.payments.get_by_consumer(consumer_id))[:limit]
        return {'payments': payments}
