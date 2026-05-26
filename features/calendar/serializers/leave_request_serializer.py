from rest_framework import serializers

class LeaveRequestSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    student_id = serializers.UUIDField()
    space_id = serializers.UUIDField()
    event_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField()
    evidence_url = serializers.CharField(read_only=True)
    status = serializers.CharField()
    processed_by = serializers.UUIDField(read_only=True)
    processed_at = serializers.DateTimeField(read_only=True)
    rejection_reason = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

class LeaveRequestCreateSerializer(serializers.Serializer):
    event_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField()
    evidence = serializers.FileField(required=False, allow_null=True)

class LeaveRequestProcessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
