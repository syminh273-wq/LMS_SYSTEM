from datetime import datetime

from django.contrib.auth.hashers import is_password_usable
from rest_framework import exceptions

from features.account.consumer.models import Consumer
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

    def get_mine(self, user):
        if not isinstance(user, Consumer):
            raise exceptions.PermissionDenied('This endpoint is only available for Consumer accounts.')
        return user

    def change_password(self, user, current_password: str, new_password: str):
        instance = self.get_mine(user)

        if not is_password_usable(getattr(instance, 'password', '')):
            raise exceptions.ValidationError({
                'detail': 'Your password is managed by Google. Please use your Google account settings to manage it.'
            })

        if not instance.check_password(current_password):
            raise exceptions.ValidationError({
                'current_password': ['Current password is incorrect.']
            })

        if instance.check_password(new_password):
            raise exceptions.ValidationError({
                'new_password': ['New password must be different from the current password.']
            })

        instance.set_password(new_password)
        instance.updated_at = datetime.now()
        return self.repository.save_password(instance)

    def register(self, data: dict):
        consumer = super().register(data)
        LMSIndexer.index_consumer(consumer)
        return consumer

    def deactivate(self, instance):
        updated = self.repository.update(instance, is_active=False)
        LMSIndexer.index_consumer(updated)
        return updated
