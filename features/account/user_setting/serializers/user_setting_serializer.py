from rest_framework import serializers

class UserSettingSerializer(serializers.Serializer):
    """Generic key-value setting serializer."""
    key = serializers.CharField()
    value = serializers.CharField()

class UserBulkSettingsSerializer(serializers.Serializer):
    """Serializer for multiple settings (dictionary input)."""
    settings = serializers.JSONField()
