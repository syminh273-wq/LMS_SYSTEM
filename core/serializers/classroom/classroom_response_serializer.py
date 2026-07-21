from rest_framework import serializers

class ClassroomResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    pid = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    teacher_id = serializers.UUIDField(read_only=True)
    max_students = serializers.IntegerField()
    status = serializers.CharField()
    pricing_type = serializers.CharField()
    price_vnd = serializers.IntegerField()
    category = serializers.CharField()
    visibility_type = serializers.CharField()
    preview_folder_uid = serializers.SerializerMethodField()
    has_access = serializers.BooleanField(read_only=True, required=False)
    has_paid = serializers.BooleanField(read_only=True, required=False)
    is_paid_classroom = serializers.SerializerMethodField()
    resolve_link = serializers.DictField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_preview_folder_uid(self, obj):
        from features.resource.repositories.resource_folder_repository import ResourceFolderRepository
        folder = ResourceFolderRepository().get_preview_folder(obj.uid)
        return str(folder.uid) if folder else None

    def get_is_paid_classroom(self, obj):
        return getattr(obj, 'pricing_type', 'free') == 'paid'
