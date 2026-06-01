from cassandra.cqlengine import columns
from django.contrib.auth.hashers import check_password, make_password
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

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
