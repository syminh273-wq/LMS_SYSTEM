from core.serializers.fields import VnDateTimeField
from features.quiz.models.quiz_question import QuizQuestion

from rest_framework import serializers


class QuizGenerateRequestSerializer(serializers.Serializer):
    num_questions = serializers.IntegerField(
        required=False, default=5, min_value=5, max_value=30,
    )
    question_type = serializers.ChoiceField(
        choices=['single_answer', 'multi_answer', 'true_false'], required=False, default='single_answer',
    )
    num_options = serializers.IntegerField(
        required=False, default=4,
        min_value=QuizQuestion.MIN_OPTIONS, max_value=QuizQuestion.MAX_OPTIONS,
        help_text="Number of answer options per question, applied uniformly when option_counts isn't set.",
    )
    option_counts = serializers.ListField(
        child=serializers.IntegerField(min_value=QuizQuestion.MIN_OPTIONS, max_value=QuizQuestion.MAX_OPTIONS),
        required=False,
        help_text="Per-question option count, e.g. [2,2,2,3,3] for a 5-question quiz where "
                   "3 questions have 2 options and 2 questions have 3 options. Overrides "
                   "num_options/num_questions when provided.",
    )
    correct_counts = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="Per-question required number of correct answers (multi_answer only), same "
                   "length as option_counts, e.g. [2,2,2,3,3] means question 4 needs exactly 3 "
                   "correct answers out of its options. Each value must not exceed that question's "
                   "option count. Ignored for single_answer (always exactly 1 correct).",
    )

    def validate(self, attrs):
        # file uploads are handled separately via request.FILES — skip the check here
        option_counts = attrs.get('option_counts')
        correct_counts = attrs.get('correct_counts')

        if option_counts:
            if 'num_questions' in self.initial_data and len(option_counts) != attrs['num_questions']:
                raise serializers.ValidationError(
                    "option_counts length must match num_questions when both are provided."
                )
            attrs['num_questions'] = len(option_counts)

        if correct_counts:
            expected_len = len(option_counts) if option_counts else attrs['num_questions']
            if len(correct_counts) != expected_len:
                raise serializers.ValidationError(
                    "correct_counts length must match num_questions/option_counts."
                )
            bounds = option_counts or [attrs.get('num_options', 4)] * expected_len
            for i, c in enumerate(correct_counts):
                if c > bounds[i]:
                    raise serializers.ValidationError(
                        f"correct_counts[{i}]={c} cannot exceed that question's option count ({bounds[i]})."
                    )

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
    opens_at   = VnDateTimeField(required=False, allow_null=True)
    closes_at  = VnDateTimeField(required=False, allow_null=True)


class QuizAssignUpdateRequestSerializer(serializers.Serializer):
    time_limit_seconds = serializers.IntegerField(required=False, min_value=0)
    max_attempts       = serializers.IntegerField(required=False, min_value=0)
    shuffle_questions  = serializers.BooleanField(required=False)
    shuffle_options    = serializers.BooleanField(required=False)
    show_explanation   = serializers.BooleanField(required=False)
    passing_score_pct  = serializers.IntegerField(required=False, min_value=0, max_value=100)
    opens_at   = VnDateTimeField(required=False, allow_null=True)
    closes_at  = VnDateTimeField(required=False, allow_null=True)


class QuizCloseRequestSerializer(serializers.Serializer):
    closes_at = VnDateTimeField(required=False, allow_null=True)


class QuizReopenRequestSerializer(serializers.Serializer):
    opens_at  = VnDateTimeField(required=False, allow_null=True)
    closes_at = VnDateTimeField(required=False, allow_null=True)


class QuizQuestionUpdateRequestSerializer(serializers.Serializer):
    question_text   = serializers.CharField(required=False)
    options         = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        min_length=QuizQuestion.MIN_OPTIONS, max_length=QuizQuestion.MAX_OPTIONS,
    )
    question_type   = serializers.ChoiceField(choices=['single_answer', 'multi_answer', 'true_false'], required=False)
    correct_answers = serializers.ListField(
        child=serializers.IntegerField(min_value=0),
        required=False, allow_empty=False,
        help_text="0-based indices into `options` (the resulting options list, if both are sent together).",
    )
    explanation    = serializers.CharField(required=False, allow_blank=True)
    order          = serializers.IntegerField(required=False)


class QuizAnswerItemSerializer(serializers.Serializer):
    question_uid = serializers.UUIDField()
    selected_answers = serializers.ListField(
        child=serializers.IntegerField(min_value=0),
        allow_empty=False,
    )


class QuizSubmitRequestSerializer(serializers.Serializer):
    answers = QuizAnswerItemSerializer(
        many=True,
        help_text="List of {question_uid, selected_answers} — selected_answers has 1 item for "
                   "single_answer questions, 2+ for multi_answer questions.",
    )
    classroom_id       = serializers.UUIDField(required=True)
    time_taken_seconds = serializers.IntegerField(required=False, default=0, min_value=0)
