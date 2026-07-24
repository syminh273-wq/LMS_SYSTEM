from rest_framework import serializers

from features.account.consumer.models.address import Address
from features.account.static_data import get_province, get_ward


VALID_TYPES = {'home', 'work', 'billing', 'other'}


class AddressReadSerializer(serializers.Serializer):
    """Read-only serializer for responses."""
    uid           = serializers.UUIDField(read_only=True)
    owner_id      = serializers.UUIDField(read_only=True)
    owner_type    = serializers.CharField(read_only=True)
    type          = serializers.CharField()
    label         = serializers.CharField(allow_blank=True, required=False)
    line1         = serializers.CharField(allow_blank=True, required=False)
    line2         = serializers.CharField(allow_blank=True, required=False)
    province_code = serializers.IntegerField()
    province_name = serializers.CharField()
    ward_code     = serializers.IntegerField()
    ward_name     = serializers.CharField()
    country       = serializers.CharField(default='Việt Nam')
    created_at    = serializers.DateTimeField(read_only=True)
    updated_at    = serializers.DateTimeField(read_only=True)

    @staticmethod
    def from_model(addr: Address) -> dict:
        return {
            'uid':           str(addr.uid),
            'owner_id':      str(addr.owner_id),
            'owner_type':    addr.owner_type,
            'type':          addr.type,
            'label':         addr.label or '',
            'line1':         addr.line1 or '',
            'line2':         addr.line2 or '',
            'province_code': addr.province_code,
            'province_name': addr.province_name,
            'ward_code':     addr.ward_code,
            'ward_name':     addr.ward_name,
            'country':       addr.country or 'Việt Nam',
            'created_at':    addr.created_at.isoformat() if addr.created_at else None,
            'updated_at':    addr.updated_at.isoformat() if addr.updated_at else None,
        }


class AddressUpsertSerializer(serializers.Serializer):
    """Write serializer. Names are auto-filled from codes by the service."""
    type          = serializers.CharField()
    label         = serializers.CharField(allow_blank=True, required=False, default='')
    line1         = serializers.CharField(allow_blank=True, required=False, default='')
    line2         = serializers.CharField(allow_blank=True, required=False, default='')
    province_code = serializers.IntegerField()
    ward_code     = serializers.IntegerField()
    country       = serializers.CharField(required=False, default='Việt Nam')

    def validate_type(self, value: str) -> str:
        if value not in VALID_TYPES:
            raise serializers.ValidationError(
                f"type phải là một trong: {sorted(VALID_TYPES)}"
            )
        return value

    def validate(self, attrs):
        province_code = attrs.get('province_code')
        ward_code     = attrs.get('ward_code')
        if not get_province(province_code):
            raise serializers.ValidationError(
                {'province_code': f'Không tồn tại tỉnh/thành với code={province_code}'}
            )
        if not get_ward(province_code, ward_code):
            raise serializers.ValidationError(
                {'ward_code': f'Không tồn tại xã/phường code={ward_code} trong tỉnh code={province_code}'}
            )
        return attrs
