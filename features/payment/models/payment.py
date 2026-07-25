from datetime import datetime
from uuid import uuid4
from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7
from features.payment.enums import PaymentStatus


class Payment(BaseTimeStampModel):
    __table_name__ = 'payments'

    uid = columns.UUID(primary_key=True, default=uuid7)

    consumer_id = columns.UUID(index=True, required=True)
    teacher_id = columns.UUID(index=True, required=False)  # populated for classroom payments so space (teacher) can query their own revenue
    order_id = columns.Text(index=True, required=True)   # unique per transaction
    request_id = columns.Text(default='')

    amount = columns.BigInt(required=True)               # VND
    order_info = columns.Text(default='')
    extra_data = columns.Text(default='')                # base64 JSON: {consumer_id, resource_type, resource_id, teacher_id}

    status = columns.Text(default=PaymentStatus.PENDING.value, index=True)
    pay_url = columns.Text(default='')                   # MoMo redirect URL
    result_code = columns.Integer(default=-1)            # MoMo result code from IPN
    trans_id = columns.BigInt(default=0)                 # MoMo transaction id

    class Meta:
        get_pk_field = 'uid'
