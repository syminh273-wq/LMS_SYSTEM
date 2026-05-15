from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    conversation_uid = serializers.UUIDField()
    msg_type = serializers.CharField()
    content = serializers.CharField(default='')
    sender_id = serializers.UUIDField(allow_null=True, required=False)
    sender_type = serializers.CharField(default='')
    sender_name = serializers.CharField(default='')
    created_at = serializers.DateTimeField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('sender_id'):
            data['sender_id'] = None

        # Build attachment object from resource fields
        resource_url = getattr(instance, 'resource_url', '') or ''
        if resource_url:
            data['attachment'] = {
                'uid': str(instance.resource_uid) if getattr(instance, 'resource_uid', None) else None,
                'url': resource_url,
                'name': getattr(instance, 'resource_name', '') or '',
                'size': getattr(instance, 'resource_size', 0) or 0,
                'type': instance.msg_type,
            }
        else:
            data['attachment'] = None
        return data
