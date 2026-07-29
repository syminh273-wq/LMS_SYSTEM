from core.serializers.fields import VnDateTimeField

from rest_framework import serializers


class ResourceFolderResponseSerializer(serializers.Serializer):
    uid = serializers.UUIDField(read_only=True)
    classroom_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    parent_folder_id = serializers.UUIDField(allow_null=True, required=False)
    owner_id = serializers.UUIDField(read_only=True)
    order_index = serializers.IntegerField(required=False, default=0)
    color = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    is_preview_only = serializers.BooleanField(required=False, default=False)
    created_at = VnDateTimeField(read_only=True)
    updated_at = VnDateTimeField(read_only=True)


class ResourceFolderTreeSerializer(ResourceFolderResponseSerializer):
    """Recursive tree node serializer.

    Instance shape: {'folder': ResourceFolder, 'children': [node, ...], 'docs': [Resource, ...]}
    as produced by ResourceFolderService.build_tree/list_tree.
    """

    def to_representation(self, instance):
        from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer

        data = super().to_representation(instance['folder'])
        data['children'] = ResourceFolderTreeSerializer(instance['children'], many=True).data
        data['docs'] = ResourceResponseSerializer(instance['docs'], many=True).data
        return data


class ResourceFolderCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    parent_folder_id = serializers.UUIDField(required=False, allow_null=True)
    order_index = serializers.IntegerField(required=False, default=0)
    color = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
    is_preview_only = serializers.BooleanField(required=False, default=False)


class ResourceFolderUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    parent_folder_id = serializers.UUIDField(required=False, allow_null=True)
    order_index = serializers.IntegerField(required=False)
    color = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
    is_preview_only = serializers.BooleanField(required=False)
