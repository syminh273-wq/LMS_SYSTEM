from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class BaseTimeStampModel(DjangoCassandraModel):
    """Abstract base cho mọi Cassandra model — timestamp + soft delete."""

    __abstract__ = True

    created_at = columns.DateTime(default=datetime.now)
    updated_at = columns.DateTime(default=datetime.now)
    is_deleted = columns.Boolean(default=False)
    deleted_at = columns.DateTime(required=False)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    @property
    def pk(self):
        return getattr(self, 'uid', None)

    @property
    def id(self):
        return self.pk


# Backward-compatible alias
BaseCassandraModel = BaseTimeStampModel
