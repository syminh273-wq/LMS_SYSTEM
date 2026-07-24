from rest_framework import serializers


class XPTransactionSerializer(serializers.Serializer):
    uid = serializers.CharField()
    event_type = serializers.CharField()
    delta_xp = serializers.IntegerField()
    ref_type = serializers.CharField(allow_blank=True, required=False)
    ref_id = serializers.CharField(allow_null=True, required=False)
    classroom_id = serializers.CharField(allow_null=True, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.CharField()
