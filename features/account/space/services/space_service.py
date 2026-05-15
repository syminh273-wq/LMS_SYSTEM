from rest_framework import exceptions
from core.backend.auth.base_auth_services import BaseAuthService
from features.account.space.repositories import Repository


class Service(BaseAuthService):
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

    def delete(self, instance):
        return self.repository.delete(instance)

    def deactivate(self, instance):
        return self.repository.update(instance, is_active=False)

    def register(self, data: dict):
        slug = data.get('slug')
        if slug and self.repository.filter(slug=slug).exists():
            raise exceptions.ValidationError({"slug": ["A space with this slug already exists."]})
        return super().register(data)
