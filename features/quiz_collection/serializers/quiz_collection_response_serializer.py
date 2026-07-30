from core.serializers.fields import VnDateTimeField

from rest_framework import serializers


class QuizCollectionItemResponseSerializer(serializers.Serializer):
    quiz_id = serializers.UUIDField(read_only=True)
    order = serializers.IntegerField()


class QuizCollectionAssignmentResponseSerializer(serializers.Serializer):
    collection_id = serializers.UUIDField(read_only=True)
    classroom_id = serializers.UUIDField(read_only=True)
    assigned_by = serializers.UUIDField(read_only=True)
    assigned_at = VnDateTimeField(read_only=True)


class QuizCollectionResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    created_by = serializers.UUIDField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    quiz_count = serializers.IntegerField()
    certificate_id = serializers.UUIDField(allow_null=True, required=False)
    certificate_name = serializers.SerializerMethodField()
    status = serializers.CharField()
    created_at = VnDateTimeField(read_only=True)
    updated_at = VnDateTimeField(read_only=True)
    progress = serializers.SerializerMethodField()

    def get_certificate_name(self, obj):
        certificate_id = obj.get('certificate_id') if isinstance(obj, dict) else obj.certificate_id
        if not certificate_id:
            return None
        cert = self.context.get('certificates_by_id', {}).get(str(certificate_id))
        return cert.name if cert else None

    def get_progress(self, obj):
        uid = obj.get('uid') if isinstance(obj, dict) else obj.uid
        progress = self.context.get('progress_by_id', {}).get(str(uid))
        if progress is None:
            return None
        return QuizCollectionProgressResponseSerializer(progress).data


class QuizCollectionDetailResponseSerializer(QuizCollectionResponseSerializer):
    items = QuizCollectionItemResponseSerializer(many=True)
    assignments = QuizCollectionAssignmentResponseSerializer(many=True)


class QuizCollectionProgressResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    passed = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    percent = serializers.FloatField()
    passed_quiz_ids = serializers.ListField(child=serializers.UUIDField())
    missing_quiz_ids = serializers.ListField(child=serializers.UUIDField())
