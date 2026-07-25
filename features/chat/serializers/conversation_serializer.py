from core.serializers.fields import VnDateTimeField

from rest_framework import serializers


class ConversationSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    type = serializers.CharField()
    name = serializers.CharField(default='')
    description = serializers.CharField(default='')
    classroom_uid = serializers.UUIDField(allow_null=True, required=False)
    member_count = serializers.IntegerField(default=0)
    last_msg_text = serializers.CharField(default='')
    last_msg_sender = serializers.CharField(default='')
    last_msg_at = VnDateTimeField(allow_null=True, required=False)
    created_at = VnDateTimeField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure None-safe fields
        if not data.get('classroom_uid'):
            data['classroom_uid'] = None
        if not data.get('last_msg_at'):
            data['last_msg_at'] = None
        return data
