from features.account.consumer.repositories import ConsumerRepository
from core.backend.auth.base_auth_services import BaseAuthService


class ConsumerService(BaseAuthService):
    def __init__(self):
        self.repository = ConsumerRepository()

    def get_by_email(self, email: str):
        return self.repository.get_by_email(email)

    def get_active_consumers(self):
        return self.repository.get_active()

    def deactivate(self, instance):
        return self.repository.update(instance, is_active=False)
