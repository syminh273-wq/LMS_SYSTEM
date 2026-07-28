from uuid import uuid4
from cassandra.cqlengine import columns
from core.models.abstract_auth import AbstractAuthModel
from core.utils.pid import generate_pid


class Space(AbstractAuthModel):
    __table_name__ = 'account_spaces'

    uid = columns.UUID(primary_key=True, default=uuid4)
    pid = columns.Text(index=True, default=generate_pid)
    email = columns.Text(index=True)
    full_name = columns.Text(default='')
    name = columns.Text(default='')
    slug = columns.Text(index=True, default='')
    description = columns.Text(default='')
    logo_url = columns.Text(default='')
    cover_url = columns.Text(default='')
    hometown = columns.Text(default='')
    date_of_birth = columns.Date(required=False)
    avatar_url = columns.Text(default='')
    learning_certificates = columns.List(columns.Text, default=[])
    contact_information = columns.Map(columns.Text, columns.Text, default={})

    # is_deleted, deleted_at, created_at, updated_at → BaseTimeStampModel
    # is_active, password, is_verified, last_login, verified_at → AbstractAuthModel
