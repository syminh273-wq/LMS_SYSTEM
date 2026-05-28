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


class PaymentInitiateResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    pay_url = serializers.CharField()
    deeplink = serializers.CharField()
    qr_code_url = serializers.CharField()
