from rest_framework import serializers

from dummy.models import Dummy


class DummyResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    owner_id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance: Dummy):
        return {
            'uid': str(instance.uid),
            'owner_id': str(instance.owner_id) if instance.owner_id else None,
            'name': instance.name or '',
            'description': instance.description or '',
            'status': instance.status or 'active',
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
            'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
        }
