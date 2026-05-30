from features.account.consumer.repositories import ConsumerRepository
from core.backend.auth.base_auth_services import BaseAuthService
from core.search_engine.typesense.indexer import LMSIndexer


class ConsumerService(BaseAuthService):
    def __init__(self):
        self.repository = ConsumerRepository()

    def get_by_email(self, email: str):
        return self.repository.get_by_email(email)

    def get_active_consumers(self):
        return self.repository.get_active()

    def register(self, data: dict):
        consumer = super().register(data)
        LMSIndexer.index_consumer(consumer)
        return consumer

    def deactivate(self, instance):
        updated = self.repository.update(instance, is_active=False)
        LMSIndexer.index_consumer(updated)
        return updated
