import json
from rest_framework import serializers
from features.account.consumer.models.teacher_settings import TeacherSetting

class TeacherSettingSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.JSONField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if isinstance(instance.value, str):
            try:
                ret['value'] = json.loads(instance.value)
            except:
                ret['value'] = {}
        return ret

class TeacherSettingBulkUpdateSerializer(serializers.Serializer):
    # This serializer will handle a dictionary of settings
    def to_internal_value(self, data):
        # We expect a dict where keys are setting keys and values are setting values
        if not isinstance(data, dict):
            raise serializers.ValidationError("Data must be a dictionary")
        return data
