from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class OTPRecord(BaseTimeStampModel):
    """OTP state per (user, user_type).

    Composite primary key: (user_uid partition, user_type clustering).
    django_cassandra_engine requires get_pk_field on composite-key
    models for .get(pk=...) routing; user_uid is the natural partition.
    """

    __table_name__ = 'account_otp_records'

    user_uid  = columns.UUID(partition_key=True, primary_key=True, required=True)
    user_type = columns.Text(primary_key=True, clustering_order='ASC', required=True)

    otp_code         = columns.Text(default='')
    email            = columns.Text(default='', index=True)
    expires_at       = columns.DateTime(required=False)
    reset_token      = columns.UUID(required=False, index=True)
    reset_expires_at = columns.DateTime(required=False)
    is_otp_verified  = columns.Boolean(default=False)
    is_reset_used    = columns.Boolean(default=False)

    class Meta:
        get_pk_field = 'user_uid'
