from core.repositories.base_repository import BaseRepository
from features.payment.models import Payment
from features.payment.utils import parse_meta


class PaymentRepository(BaseRepository):
    model = Payment

    def get_by_order_id(self, order_id: str):
        return self.model.objects.filter(order_id=order_id).first()

    def get_by_consumer(self, consumer_id):
        return self.model.objects.filter(consumer_id=consumer_id, is_deleted=False)

    def get_by_teacher(self, teacher_id, status: str | None = None, limit: int = 50):
        """Payments received by a teacher (classroom payments only)."""
        qs = self.model.objects.filter(teacher_id=teacher_id, is_deleted=False)
        if status:
            qs = qs.filter(status=status)
        return qs.limit(limit)

    def find_existing_for_resource(self, consumer_id, resource_type: str, resource_id: str):
        """Return the most recent active payment (pending or completed) for this
        consumer + resource. `resource_id` is matched inside the extra_data
        blob — Cassandra has no native JSON index, so we filter by consumer_id
        (indexed) and decode in Python.
        """
        target = str(resource_id)
        for p in self.model.objects.filter(consumer_id=consumer_id, is_deleted=False).limit(200):
            meta = parse_meta(getattr(p, 'extra_data', '') or '')
            if meta.get('resource_type') == resource_type and str(meta.get('resource_id')) == target:
                if (p.status or '') in ('pending', 'completed'):
                    return p
        return None
