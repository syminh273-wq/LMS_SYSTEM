from rest_framework import serializers


QUIZ_TYPE_CHOICES = ['multiple_choice', 'true_false', 'fill_blank', 'scenario']


class QuizGenerateRequestSerializer(serializers.Serializer):
    content     = serializers.CharField(required=False, allow_blank=False)
    resource_id = serializers.UUIDField(required=False)
    quiz_type = serializers.ChoiceField(
        choices=QUIZ_TYPE_CHOICES, required=False, default='multiple_choice',
    )
    num_questions = serializers.IntegerField(
        required=False, default=10, min_value=5, max_value=30,
    )
    max_content_length = serializers.IntegerField(
        required=False, default=12000, min_value=1000, max_value=40000,
    )

    def validate(self, attrs):
        # file uploads are handled separately via request.FILES — skip the check here
        return attrs


class QuizUpdateRequestSerializer(serializers.Serializer):
    title       = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status      = serializers.ChoiceField(choices=['draft', 'published', 'archived'], required=False)


class QuizAssignRequestSerializer(serializers.Serializer):
    classroom_id       = serializers.UUIDField(required=True)
    time_limit_seconds = serializers.IntegerField(required=False, default=0, min_value=0)
    max_attempts       = serializers.IntegerField(required=False, default=0, min_value=0)
    shuffle_questions  = serializers.BooleanField(required=False, default=False)
    shuffle_options    = serializers.BooleanField(required=False, default=False)
    show_explanation   = serializers.BooleanField(required=False, default=True)
    passing_score_pct  = serializers.IntegerField(required=False, default=50, min_value=0, max_value=100)


class QuizAssignUpdateRequestSerializer(serializers.Serializer):
    time_limit_seconds = serializers.IntegerField(required=False, min_value=0)
    max_attempts       = serializers.IntegerField(required=False, min_value=0)
    shuffle_questions  = serializers.BooleanField(required=False)
    shuffle_options    = serializers.BooleanField(required=False)
    show_explanation   = serializers.BooleanField(required=False)
    passing_score_pct  = serializers.IntegerField(required=False, min_value=0, max_value=100)


class QuizQuestionUpdateRequestSerializer(serializers.Serializer):
    question_text  = serializers.CharField(required=False)
    option_a       = serializers.CharField(required=False)
    option_b       = serializers.CharField(required=False)
    option_c       = serializers.CharField(required=False)
    option_d       = serializers.CharField(required=False)
    correct_answer = serializers.ChoiceField(choices=['a', 'b', 'c', 'd'], required=False)
    explanation    = serializers.CharField(required=False, allow_blank=True)
    order          = serializers.IntegerField(required=False)


class QuizSubmitRequestSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.ChoiceField(choices=['a', 'b', 'c', 'd']),
        help_text="Map of question_uid → chosen answer letter (a/b/c/d)"
    )
    classroom_id       = serializers.UUIDField(required=True)
    time_taken_seconds = serializers.IntegerField(required=False, default=0, min_value=0)
