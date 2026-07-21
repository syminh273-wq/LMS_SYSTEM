import base64
import json

from rest_framework import serializers


class PaymentResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    consumer_id = serializers.UUIDField(read_only=True)
    order_id = serializers.CharField(read_only=True)
    amount = serializers.IntegerField(read_only=True)
    order_info = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    pay_url = serializers.CharField(read_only=True)
    result_code = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    resource_type = serializers.SerializerMethodField()
    resource_id = serializers.SerializerMethodField()

    def get_resource_type(self, obj):
        try:
            meta = json.loads(base64.b64decode(obj.extra_data).decode())
            return meta.get('resource_type')
        except Exception:
            return None

    def get_resource_id(self, obj):
        try:
            meta = json.loads(base64.b64decode(obj.extra_data).decode())
            return meta.get('resource_id')
        except Exception:
            return None


class PaymentInitiateResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    pay_url = serializers.CharField()
    deeplink = serializers.CharField()
    qr_code_url = serializers.CharField()
