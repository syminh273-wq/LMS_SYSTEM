from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7

class Classroom(BaseTimeStampModel):
    uid = columns.UUID(primary_key=True, default=uuid7)
    pid = columns.Text(index=True)
    name = columns.Text(required=True)
    description = columns.Text(default='')
    teacher_id = columns.UUID(index=True, required=True)
    max_students = columns.Integer(default=0)
    status = columns.Text(default='active')
    pricing_type = columns.Text(default='free', index=True)
    price_vnd = columns.BigInt(default=0)
    category = columns.Text(default='other', index=True)
    visibility_type = columns.Text(default='public', index=True)

    class Meta:
        get_pk_field = 'uid'

    __table_name__ = 'account_classrooms'
