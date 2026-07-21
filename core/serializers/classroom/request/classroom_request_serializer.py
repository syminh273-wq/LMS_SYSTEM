from rest_framework import serializers

CATEGORY_CHOICES = [
    'math', 'physics', 'chemistry', 'biology', 'language',
    'programming', 'business', 'design', 'music', 'other',
]
VISIBILITY_CHOICES = ['public', 'private']


class ClassroomRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    max_students = serializers.IntegerField(required=False, default=0)
    status = serializers.ChoiceField(choices=['active', 'private'], required=False, default='active')
    pricing_type = serializers.ChoiceField(choices=['free', 'paid'], required=False, default='free')
    price_vnd = serializers.IntegerField(required=False, default=0, min_value=0)
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES, required=False, default='other')
    visibility_type = serializers.ChoiceField(choices=VISIBILITY_CHOICES, required=False, default='public')

    def validate(self, attrs):
        if attrs.get('pricing_type') == 'paid':
            price = int(attrs.get('price_vnd') or 0)
            if price < 1000:
                raise serializers.ValidationError(
                    {'price_vnd': 'Lớp học trả phí phải có giá tối thiểu 1.000 VND.'}
                )
        return attrs
