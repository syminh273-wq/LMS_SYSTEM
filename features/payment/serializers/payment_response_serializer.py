from core.serializers.fields import VnDateTimeField

import base64
import json

from rest_framework import serializers


def decode_meta(extra_data: str) -> dict:
    if not extra_data:
        return {}
    try:
        return json.loads(base64.b64decode(extra_data).decode())
    except Exception:
        return {}


class PaymentResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    consumer_id = serializers.UUIDField(read_only=True)
    teacher_id = serializers.UUIDField(read_only=True, required=False, allow_null=True)
    order_id = serializers.CharField(read_only=True)
    amount = serializers.IntegerField(read_only=True)
    order_info = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    pay_url = serializers.CharField(read_only=True)
    result_code = serializers.IntegerField(read_only=True)
    trans_id = serializers.IntegerField(read_only=True)
    created_at = VnDateTimeField(read_only=True)
    updated_at = VnDateTimeField(read_only=True)
    resource_type = serializers.SerializerMethodField()
    resource_id = serializers.SerializerMethodField()

    def get_resource_type(self, obj):
        return decode_meta(getattr(obj, 'extra_data', '')).get('resource_type')

    def get_resource_id(self, obj):
        return decode_meta(getattr(obj, 'extra_data', '')).get('resource_id')


class PaymentInitiateResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    pay_url = serializers.CharField()
    deeplink = serializers.CharField()
    qr_code_url = serializers.CharField()
    status = serializers.CharField(required=False, allow_blank=True)
