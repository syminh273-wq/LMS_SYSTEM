import uuid
from django.db import models
from .mixins.timestamp import TimeStampMixin
from .mixins.soft_deletion import SoftDeletionMixin
from .mixins.audit_log import AuditLogMixin


class BaseModel(TimeStampMixin, SoftDeletionMixin, AuditLogMixin):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
