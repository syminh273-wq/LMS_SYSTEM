from datetime import datetime
from typing import Any, Optional, Type


class BaseRepository:
    model: Type[Any]
    @property
    def _is_cassandra(self) -> bool:
        try:
            from django_cassandra_engine.models import DjangoCassandraModel
            return issubclass(self.model, DjangoCassandraModel)
        except ImportError:
            return False

    @property
    def _db_alias(self) -> Optional[str]:
        return getattr(self.model, '__db_alias__', None)

    def _qs(self):
        """Return the base queryset routed to the correct database."""
        if self._is_cassandra:
            return self.model.objects
        alias = self._db_alias
        return self.model.objects.using(alias) if alias else self.model.objects

    def _filter_qs(self, qs, **kwargs):
        """Apply .filter() and add .allow_filtering() for Cassandra."""
        qs = qs.filter(**kwargs)
        if self._is_cassandra:
            return qs.allow_filtering()
        return qs

    def all(self):
        qs = self._qs()
        if hasattr(self.model, 'is_deleted'):
            return self._filter_qs(qs, is_deleted=False)
        return qs.all()

    def get(self, **kwargs):
        return self._qs().get(**kwargs)

    def filter(self, **kwargs):
        return self._filter_qs(self._qs(), **kwargs)

    def create(self, **kwargs):
        return self._qs().create(**kwargs)

    def update(self, instance: Any, **kwargs) -> Any:
        if self._is_cassandra:
            instance.update(**kwargs)
            for k, v in kwargs.items():
                setattr(instance, k, v)
        else:
            for k, v in kwargs.items():
                setattr(instance, k, v)
            instance.save()
        return instance

    def delete(self, instance: Any):
        if self._is_cassandra:
            instance.update(is_deleted=True, deleted_at=datetime.now())
        else:
            instance.is_deleted = True
            instance.deleted_at = datetime.now()
            instance.save(update_fields=['is_deleted', 'deleted_at'])

    def find(self, uid: Any):
        if self._is_cassandra:
            instance = self._qs().get(uid=uid)
            if getattr(instance, 'is_deleted', False):
                raise self.model.DoesNotExist(f'{self.model.__name__} not found.')
            return instance
        alias = self._db_alias
        qs = self.model.objects.using(alias) if alias else self.model.objects
        lookup = {'uid': uid}
        if hasattr(self.model, 'is_deleted'):
            lookup['is_deleted'] = False
        return qs.get(**lookup)
