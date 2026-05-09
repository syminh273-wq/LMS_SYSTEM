from core.repositories.base_repository import BaseRepository
from features.account.consumer.models import Consumer


class ConsumerRepository(BaseRepository):
    model = Consumer

    def get_by_email(self, email: str):
        instance = self.filter(email=email, is_deleted=False).first()
        if instance is None:
            raise Consumer.DoesNotExist('Consumer not found.')
        return instance

    def get_by_username(self, username: str):
        instance = self.filter(username=username, is_deleted=False).first()
        if instance is None:
            raise Consumer.DoesNotExist('Consumer not found.')
        return instance

    def get_by_role(self, role: str):
        return self.filter(role=role, is_deleted=False)

    def get_active(self):
        return self.filter(is_active=True, is_deleted=False)
