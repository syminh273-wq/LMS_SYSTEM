from rest_framework import serializers


class PaymentRequestSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1000)          # VND, min 1000
    order_info = serializers.CharField(max_length=255)
    resource_type = serializers.ChoiceField(choices=['classroom'])
    resource_id = serializers.UUIDField()
