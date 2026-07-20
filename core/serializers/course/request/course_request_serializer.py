from rest_framework import serializers


class CourseRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    cover_url = serializers.CharField(required=False, allow_blank=True, default='')
    pricing_type = serializers.ChoiceField(choices=['free', 'paid'], required=False, default='free')
    price_vnd = serializers.IntegerField(required=False, default=0, min_value=0)
    status = serializers.ChoiceField(
        choices=['draft', 'published', 'archived'], required=False, default='draft'
    )

    def validate(self, data):
        if data.get('pricing_type') == 'paid':
            price = int(data.get('price_vnd') or 0)
            if price < 1000:
                raise serializers.ValidationError(
                    {'price_vnd': 'Khóa học trả phí phải có giá tối thiểu 1.000đ.'}
                )
        else:
            data['price_vnd'] = 0
        return data


class CourseLessonRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    video_resource_uid = serializers.UUIDField(required=False, allow_null=True)
    material_resource_uids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True, default=list
    )
    duration_seconds = serializers.IntegerField(required=False, default=0, min_value=0)
    is_preview = serializers.BooleanField(required=False, default=False)
    is_published = serializers.BooleanField(required=False, default=True)
    order_index = serializers.IntegerField(required=False, allow_null=True)
