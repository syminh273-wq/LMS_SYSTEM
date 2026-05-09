from django.db import models


class AuditLogMixin(models.Model):
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True
