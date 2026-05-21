from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from features.quiz.serializers.quiz_request_serializer import QuizSubmitRequestSerializer
from features.quiz.serializers.quiz_response_serializer import (
    QuizResponseSerializer,
    QuizPublicDetailResponseSerializer,
    QuizAttemptResponseSerializer,
)
from features.quiz.services.quiz_service import QuizService


class ConsumerQuizViewSet(ViewSet):
    """Student-facing quiz endpoints. Correct answers are never exposed."""

    service = QuizService()

    # ── LIST  GET /consumer/quiz/?classroom_id=<uid> ──────────────────────
    def list(self, request):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        quizzes = self.service.get_by_classroom(classroom_id)
        return Response(QuizResponseSerializer(list(quizzes), many=True).data)

    # ── RETRIEVE  GET /consumer/quiz/<uid>/?classroom_id=<id> ─────────────
    def retrieve(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        quiz, questions = self.service.get_with_questions(pk)

        data = QuizPublicDetailResponseSerializer({
            **{f: getattr(quiz, f) for f in [
                'uid', 'created_by', 'resource_id',
                'title', 'description', 'questions_count', 'status',
                'created_at', 'updated_at',
            ]},
            'questions': questions,
            'time_limit_seconds': 0,
            'max_attempts': 0,
        }).data

        # Inject classroom-specific settings from the assignment
        if classroom_id:
            assignment = self.service.get_assignment(pk, classroom_id)
            if assignment:
                data['time_limit_seconds'] = assignment.time_limit_seconds or 0
                data['max_attempts'] = assignment.max_attempts or 0
                data['shuffle_questions'] = assignment.shuffle_questions or False
                data['shuffle_options'] = assignment.shuffle_options or False
                data['show_explanation'] = assignment.show_explanation or True
                data['passing_score_pct'] = assignment.passing_score_pct or 50

        return Response(data)

    # ── MY ATTEMPTS  GET /consumer/quiz/<uid>/attempts/?classroom_id=<id> ─
    @action(detail=True, methods=['get'], url_path='attempts')
    def attempts(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        my_attempts = self.service.get_student_attempts(pk, classroom_id, request.user.uid)
        return Response(QuizAttemptResponseSerializer(list(my_attempts), many=True).data)

    # ── SUBMIT  POST /consumer/quiz/<uid>/submit/ ─────────────────────────
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        serializer = QuizSubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers            = serializer.validated_data['answers']
        classroom_id       = str(serializer.validated_data['classroom_id'])
        time_taken_seconds = serializer.validated_data.get('time_taken_seconds', 0)

        # Get assignment to read this classroom's settings
        assignment = self.service.get_assignment(pk, classroom_id)

        # Enforce max_attempts for this classroom
        if assignment and assignment.max_attempts and assignment.max_attempts > 0:
            attempt_count = self.service.get_student_attempt_count(pk, classroom_id, request.user.uid)
            if attempt_count >= assignment.max_attempts:
                return Response(
                    {'detail': f'Bạn đã sử dụng hết {assignment.max_attempts} lần làm bài trong lớp này.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        attempt_count = self.service.get_student_attempt_count(pk, classroom_id, request.user.uid)
        _, questions = self.service.get_with_questions(pk)

        results = []
        correct_count = 0
        for question in questions:
            q_uid = str(question.uid)
            chosen = answers.get(q_uid)
            is_correct = chosen == question.correct_answer if chosen else False
            if is_correct:
                correct_count += 1
            results.append({
                'question_uid': q_uid,
                'question_text': question.question_text,
                'chosen': chosen,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation,
            })

        total = len(questions)
        score_pct = round((correct_count / total * 100) if total else 0, 1)
        attempt_number = attempt_count + 1

        # Check if student passed
        passing_score = (assignment.passing_score_pct or 50) if assignment else 50
        is_passed = score_pct >= passing_score

        self.service.record_attempt(
            quiz_uid=pk,
            classroom_id=classroom_id,
            student_uid=request.user.uid,
            attempt_number=attempt_number,
            score=correct_count,
            total_questions=total,
            score_pct=int(score_pct),
            time_taken_seconds=time_taken_seconds,
            answers={str(k): str(v) for k, v in answers.items()},
        )

        max_attempts = (assignment.max_attempts or 0) if assignment else 0
        attempts_remaining = (max_attempts - attempt_number) if max_attempts > 0 else None

        show_exp = (assignment.show_explanation or True) if assignment else True
        if not show_exp:
            for r in results:
                r.pop('explanation', None)
                r.pop('correct_answer', None)

        return Response({
            'total': total,
            'correct': correct_count,
            'score': score_pct,
            'is_passed': is_passed,
            'passing_score': passing_score,
            'attempt_number': attempt_number,
            'attempts_used': attempt_number,
            'attempts_remaining': attempts_remaining,
            'results': results,
            'show_explanation': show_exp,
        })
