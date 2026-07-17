from rest_framework import serializers


class ResourceFolderResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    classroom_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    parent_folder_id = serializers.UUIDField(allow_null=True, required=False)
    owner_id = serializers.UUIDField(read_only=True)
    order_index = serializers.IntegerField(required=False, default=0)
    color = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ResourceFolderCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    parent_folder_id = serializers.UUIDField(required=False, allow_null=True)
    order_index = serializers.IntegerField(required=False, default=0)
    color = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)


class ResourceFolderUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    parent_folder_id = serializers.UUIDField(required=False, allow_null=True)
    order_index = serializers.IntegerField(required=False)
    color = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
