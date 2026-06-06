from uuid import uuid4
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel


class OTPRecord(BaseTimeStampModel):
    __table_name__ = 'account_otp_records'

    class Meta:
        get_pk_field = 'user_uid'

    user_uid = columns.UUID(primary_key=True)
    user_type = columns.Text(primary_key=True, clustering_order='ASC')  # 'consumer' or 'space'
    otp_code = columns.Text(default='')
    email = columns.Text(default='', index=True)
    expires_at = columns.DateTime(required=False)
    reset_token = columns.UUID(required=False, index=True)
    reset_expires_at = columns.DateTime(required=False)
    is_otp_verified = columns.Boolean(default=False)
    is_reset_used = columns.Boolean(default=False)
