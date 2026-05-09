from uuid import uuid4
from cassandra.cqlengine import columns
from core.models.abstract_auth import AbstractAuthModel
from features.account.consumer.enums import ConsumerRole


class Consumer(AbstractAuthModel):
    __table_name__ = 'account_consumers'

    uid = columns.UUID(primary_key=True, default=uuid4)
    username = columns.Text(index=True, default='')
    email = columns.Text(index=True, default='')
    full_name = columns.Text(default='')
    phone = columns.Text(default='')
    avatar_url = columns.Text(default='')
    role = columns.Text(default=ConsumerRole.STUDENT.value, index=True)

    # is_deleted, deleted_at, created_at, updated_at → BaseTimeStampModel
    # password, is_verified, is_active, last_login, verified_at → AbstractAuthModel
