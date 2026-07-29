from core.serializers.fields import VnDateTimeField

from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    conversation_uid = serializers.UUIDField()
    msg_type = serializers.CharField()
    content = serializers.CharField(default='')
    sender_id = serializers.UUIDField(allow_null=True, required=False)
    sender_type = serializers.CharField(default='')
    sender_name = serializers.CharField(default='')
    sender_avatar = serializers.CharField(default='', required=False)
    created_at = VnDateTimeField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('sender_id'):
            data['sender_id'] = None
        data['sender_avatar'] = self._resolve_avatar(instance)

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

    @staticmethod
    def _resolve_avatar(instance) -> str:
        """Look up avatar from the per-request batch cache populated by
        ``attach_avatars`` (called by the viewset before serialization)."""
        cache = getattr(instance, '_avatar_cache', None)
        if cache is not None:
            sender_id = getattr(instance, 'sender_id', None)
            if sender_id:
                entry = cache.get(str(sender_id))
                if entry:
                    return entry.avatar_url or ''
            return ''
        return ''


def attach_avatars(messages):
    """Batch fetch SocialProfile rows for all senders in ``messages`` and attach
    them as a transient ``_avatar_cache`` attribute on each message instance.

    Call this once in the viewset before passing messages to the serializer.
    """
    from features.social.repositories.profile_repository import ProfileRepository

    sender_ids = {
        str(m.sender_id) for m in messages if getattr(m, 'sender_id', None)
    }
    if not sender_ids:
        for m in messages:
            m._avatar_cache = {}
        return
    cache = ProfileRepository().get_by_owners(sender_ids)
    for m in messages:
        m._avatar_cache = cache

