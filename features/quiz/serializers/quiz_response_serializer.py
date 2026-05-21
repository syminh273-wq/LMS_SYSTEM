from rest_framework import serializers


class QuizQuestionSerializer(serializers.Serializer):
    uid           = serializers.UUIDField(read_only=True)
    quiz_id       = serializers.UUIDField(read_only=True)
    question_text = serializers.CharField()
    option_a      = serializers.CharField()
    option_b      = serializers.CharField()
    option_c      = serializers.CharField()
    option_d      = serializers.CharField()
    correct_answer = serializers.CharField()
    explanation   = serializers.CharField()
    order         = serializers.IntegerField()
    created_at    = serializers.DateTimeField(read_only=True)


class QuizQuestionPublicSerializer(serializers.Serializer):
    """For students — omits correct_answer and explanation."""
    uid           = serializers.UUIDField(read_only=True)
    quiz_id       = serializers.UUIDField(read_only=True)
    question_text = serializers.CharField()
    option_a      = serializers.CharField()
    option_b      = serializers.CharField()
    option_c      = serializers.CharField()
    option_d      = serializers.CharField()
    order         = serializers.IntegerField()


class QuizResponseSerializer(serializers.Serializer):
    uid             = serializers.UUIDField(read_only=True)
    created_by      = serializers.UUIDField(read_only=True)
    resource_id     = serializers.UUIDField(read_only=True)
    title           = serializers.CharField()
    description     = serializers.CharField()
    questions_count = serializers.IntegerField()
    status          = serializers.CharField()
    created_at      = serializers.DateTimeField(read_only=True)
    updated_at      = serializers.DateTimeField(read_only=True)


class QuizDetailResponseSerializer(QuizResponseSerializer):
    questions = QuizQuestionSerializer(many=True)


class QuizPublicDetailResponseSerializer(QuizResponseSerializer):
    """For students — questions without answers. Settings injected from assignment."""
    questions          = QuizQuestionPublicSerializer(many=True)
    time_limit_seconds = serializers.IntegerField(default=0)
    max_attempts       = serializers.IntegerField(default=0)
    shuffle_questions  = serializers.BooleanField(default=False)
    shuffle_options    = serializers.BooleanField(default=False)
    show_explanation   = serializers.BooleanField(default=True)
    passing_score_pct  = serializers.IntegerField(default=50)


class QuizAssignmentResponseSerializer(serializers.Serializer):
    quiz_id            = serializers.UUIDField(read_only=True)
    classroom_id       = serializers.UUIDField(read_only=True)
    assigned_by        = serializers.UUIDField(read_only=True)
    assigned_at        = serializers.DateTimeField(read_only=True)
    time_limit_seconds = serializers.IntegerField(default=0)
    max_attempts       = serializers.IntegerField(default=0)
    shuffle_questions  = serializers.BooleanField(default=False)
    shuffle_options    = serializers.BooleanField(default=False)
    show_explanation   = serializers.BooleanField(default=True)
    passing_score_pct  = serializers.IntegerField(default=50)


class QuizAttemptResponseSerializer(serializers.Serializer):
    uid                = serializers.UUIDField(read_only=True)
    quiz_id            = serializers.UUIDField(read_only=True)
    classroom_id       = serializers.UUIDField(read_only=True)
    student_id         = serializers.UUIDField(read_only=True)
    attempt_number     = serializers.IntegerField()
    score              = serializers.IntegerField()
    total_questions    = serializers.IntegerField()
    score_pct          = serializers.IntegerField()
    time_taken_seconds = serializers.IntegerField()
    submitted_at       = serializers.DateTimeField(read_only=True)
