from rest_framework import serializers


class DocReadingProgressResponseSerializer(serializers.Serializer):
    classroom_id = serializers.UUIDField()
    student_id = serializers.UUIDField()
    resource_uid = serializers.UUIDField()
    read_progress = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    note_count = serializers.IntegerField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)
    last_opened_at = serializers.DateTimeField(allow_null=True, required=False)


class DocNoteResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    resource_uid = serializers.UUIDField()
    classroom_id = serializers.UUIDField()
    student_id = serializers.UUIDField()
    content = serializers.CharField()
    page = serializers.IntegerField(allow_null=True, required=False)
    x_pct = serializers.FloatField(allow_null=True, required=False)
    y_pct = serializers.FloatField(allow_null=True, required=False)
    progress_at = serializers.FloatField()
    color = serializers.CharField()
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    updated_at = serializers.DateTimeField(allow_null=True, required=False)


class DocNoteCreateRequestSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000)
    page = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    x_pct = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=1)
    y_pct = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=1)
    progress_at = serializers.FloatField(required=False, min_value=0, max_value=1)
    color = serializers.CharField(max_length=32, required=False, allow_blank=True)


class DocNoteUpdateRequestSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000, required=False)
    page = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    x_pct = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=1)
    y_pct = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=1)
    progress_at = serializers.FloatField(required=False, min_value=0, max_value=1)
    color = serializers.CharField(max_length=32, required=False, allow_blank=True)


class ProgressCompleteRequestSerializer(serializers.Serializer):
    is_completed = serializers.BooleanField(required=False, default=True)
