from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class AbstractAuthModel(BaseTimeStampModel):
    """Abstract Cassandra model cho bất kỳ entity nào cần xác thực."""

    __abstract__ = True

    password = columns.Text(default='')
    is_verified = columns.Boolean(default=False)
    is_active = columns.Boolean(default=True)
    last_login = columns.DateTime(required=False)
    verified_at = columns.DateTime(required=False)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
