from uuid import uuid4
from cassandra.cqlengine import columns

from core.models.cassandra import BaseTimeStampModel


class Address(BaseTimeStampModel):
    """
    Address book entry — 1 row per (owner_id, owner_type).
    Owner can be a Consumer (student) or a Space (teacher/brand).
    Provinces/wards are stored as codes (post-2025 VN admin reform) plus
    snapshot names so we never need to join against an external reference
    at render time.
    """

    __table_name__ = "account_addresses"

    owner_id   = columns.UUID(partition_key=True, required=True)   # Consumer.uid or Space.uid
    owner_type = columns.Text(partition_key=True, required=True)   # 'consumer' | 'space'
    uid = columns.UUID(primary_key=True, default=uuid4, clustering_order="DESC")

    type  = columns.Text(required=True)                    # home | work | billing | other
    label = columns.Text(default="")                       # user-given label, e.g. "Nhà mẹ"

    line1 = columns.Text(default="")                       # street line 1 (number + street)
    line2 = columns.Text(default="")                       # apt / building / floor (optional)

    province_code = columns.Integer(required=True)
    province_name = columns.Text(required=True)
    ward_code     = columns.Integer(required=True)
    ward_name     = columns.Text(required=True)

    country = columns.Text(default="Việt Nam")

    class Meta:
        get_pk_field = "uid"
