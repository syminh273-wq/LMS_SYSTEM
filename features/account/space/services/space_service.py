from datetime import datetime

from django.contrib.auth.hashers import is_password_usable
from rest_framework import exceptions
from core.backend.auth.base_auth_services import BaseAuthService
from features.account.space.models import Space
from features.account.space.repositories import Repository


class Service(BaseAuthService):
    editable_profile_fields = {
        'full_name',
        'hometown',
        'date_of_birth',
        'avatar_url',
        'learning_certificates',
        'contact_information',
    }

    def __init__(self):
        self.repository = Repository()

    def all(self):
        return self.repository.all()

    def find(self, uid):
        return self.repository.find(uid)

    def get_by_slug(self, slug: str):
        return self.repository.get_by_slug(slug)

    def get_active_spaces(self):
        return self.repository.get_active()

    def update(self, instance, **kwargs):
        return self.repository.update(instance, **kwargs)

    def get_mine(self, user):
        if not isinstance(user, Space):
            raise exceptions.PermissionDenied('This endpoint is only available for Space accounts.')
        return user

    def update_mine(self, user, data: dict):
        instance = self.get_mine(user)
        profile_data = {
            key: value
            for key, value in data.items()
            if key in self.editable_profile_fields
        }
        if profile_data:
            profile_data['updated_at'] = datetime.now()
            instance = self.repository.update_profile(instance, **profile_data)
        return instance

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

    def delete(self, instance):
        return self.repository.delete(instance)

    def deactivate(self, instance):
        return self.repository.update(instance, is_active=False)

    def register(self, data: dict):
        slug = data.get('slug')
        if slug and self.repository.filter(slug=slug).exists():
            raise exceptions.ValidationError({"slug": ["A space with this slug already exists."]})
        return super().register(data)
