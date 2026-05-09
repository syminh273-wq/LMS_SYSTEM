from typing import Any
from core.repositories.base_repository import BaseRepository


class BaseService:
    repository: BaseRepository

    def all(self):
        return self.repository.all()

    def find(self, uid: Any):
        return self.repository.find(uid)

    def filter(self, **kwargs):
        return self.repository.filter(**kwargs)

    def create(self, **kwargs):
        return self.repository.create(**kwargs)

    def update(self, instance: Any, **kwargs):
        return self.repository.update(instance, **kwargs)

    def delete(self, instance: Any):
        return self.repository.delete(instance)
