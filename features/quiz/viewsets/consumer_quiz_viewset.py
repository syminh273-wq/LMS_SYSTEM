import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.views.mixins import ConsumerScopeMixin
from features.quiz.serializers.quiz_request_serializer import QuizSubmitRequestSerializer
from features.quiz.serializers.quiz_response_serializer import (
    QuizResponseSerializer,
    QuizPublicDetailResponseSerializer,
    QuizLogResponseSerializer,
)
from features.quiz.serializers.quiz_leaderboard_serializer import (
    QuizLeaderboardResponseSerializer,
    QuizLeaderboardStudentDetailSerializer,
)
from features.quiz.services.quiz_service import QuizService
from features.quiz.services.quiz_leaderboard_service import QuizLeaderboardService

logger = logging.getLogger(__name__)


class ConsumerQuizViewSet(ConsumerScopeMixin, ViewSet):
    """Student-facing quiz endpoints. Correct answers are never exposed."""

    service = QuizService()
    leaderboard_service = QuizLeaderboardService()

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
                data['show_explanation'] = bool(assignment.show_explanation)
                data['passing_score_pct'] = assignment.passing_score_pct or 50
                status_payload = self.service.get_assignment_status(pk, classroom_id)
                data['is_closed'] = status_payload['is_closed']
                data['is_open'] = status_payload['is_open']
                data['is_expired'] = status_payload['is_expired']
                data['is_not_yet_open'] = status_payload.get('is_not_yet_open', False)
                data['opens_at'] = status_payload['opens_at']
                data['closes_at'] = status_payload['closes_at']
                data['closed_at'] = status_payload['closed_at']
                data['server_now'] = status_payload.get('server_now')
            else:
                data['is_closed'] = False
                data['is_open'] = True
                data['is_expired'] = False
                data['is_not_yet_open'] = False

        return Response(data)

    # ── MY ATTEMPTS  GET /consumer/quiz/<uid>/attempts/?classroom_id=<id> ─
    @action(detail=True, methods=['get'], url_path='attempts')
    def attempts(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        my_attempts = self.service.get_student_attempts(pk, classroom_id, request.user.uid)
        return Response(QuizLogResponseSerializer(list(my_attempts), many=True).data)

    # ── LEADERBOARD  GET /consumer/quiz/<uid>/leaderboard/?classroom_id=<id> ─
    @action(detail=True, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request, pk=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        status_payload = self.service.get_assignment_status(pk, classroom_id)
        try:
            limit = int(request.query_params.get('limit', 20))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))
        payload = self.leaderboard_service.build(
            quiz_id=pk,
            classroom_id=classroom_id,
            limit=limit,
        )
        payload['closed_at'] = status_payload['closed_at']
        payload['closes_at'] = status_payload['closes_at']
        return Response(QuizLeaderboardResponseSerializer(payload).data)

    # ── STUDENT DETAIL  GET /consumer/quiz/<uid>/leaderboard/<student_uid>/?classroom_id=<id> ─
    @action(detail=True, methods=['get'], url_path=r'leaderboard/(?P<student_uid>[^/.]+)')
    def leaderboard_student(self, request, pk=None, student_uid=None):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        status_payload = self.service.get_assignment_status(pk, classroom_id)
        payload = self.leaderboard_service.student_detail(
            quiz_id=pk,
            classroom_id=classroom_id,
            student_id=student_uid,
        )
        return Response(QuizLeaderboardStudentDetailSerializer(payload).data)

    # ── SUBMIT  POST /consumer/quiz/<uid>/submit/ ─────────────────────────
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        serializer = QuizSubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers            = serializer.validated_data['answers']
        classroom_id       = str(serializer.validated_data['classroom_id'])
        time_taken_seconds = serializer.validated_data.get('time_taken_seconds', 0)
        student_id         = request.user.uid

        if not self.service.is_classroom_member(classroom_id, student_id):
            return Response(
                {'detail': 'Bạn không phải là thành viên của lớp học này.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = self.service.get_assignment(pk, classroom_id)
        status_payload = self.service.get_assignment_status(pk, classroom_id, assignment=assignment)

        blocked_response = self._reject_if_not_submittable(assignment, status_payload)
        if blocked_response:
            return blocked_response

        attempt_count = self.service.get_student_attempt_count(pk, classroom_id, student_id)
        attempts_blocked_response = self._reject_if_out_of_attempts(assignment, attempt_count)
        if attempts_blocked_response:
            return attempts_blocked_response

        _, questions = self.service.get_with_questions(pk)
        results, correct_count = self._grade_answers(questions, answers)
        total = len(questions)
        score_pct = round((correct_count / total * 100) if total else 0, 1)
        attempt_number = attempt_count + 1
        passing_score = (assignment.passing_score_pct or 50) if assignment else 50
        is_passed = score_pct >= passing_score

        self.service.record_attempt(
            quiz_uid=pk,
            classroom_id=classroom_id,
            student_uid=student_id,
            attempt_number=attempt_number,
            score=correct_count,
            total_questions=total,
            score_pct=round(score_pct),
            time_taken_seconds=time_taken_seconds,
            answers={str(k): str(v) for k, v in answers.items()},
        )

        self._link_exam_submission(pk, classroom_id, student_id, answers, time_taken_seconds)
        certificate_issued_payload = self._issue_certificates(pk, classroom_id, student_id)

        max_attempts = (assignment.max_attempts or 0) if assignment else 0
        attempts_remaining = (max_attempts - attempt_number) if max_attempts > 0 else None

        show_explanation = bool(assignment.show_explanation) if assignment else True
        if not show_explanation:
            self._strip_answer_key(results)

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
            'show_explanation': show_explanation,
            'certificate_issued': certificate_issued_payload,
        })

    def _reject_if_not_submittable(self, assignment, status_payload):
        """403 Response if the assignment isn't open for submission right now, else None."""
        if assignment is None:
            return None

        if status_payload.get('is_not_yet_open'):
            return Response(
                {
                    'detail': 'Bài quiz chưa mở, vui lòng quay lại sau.',
                    'reason': 'not_yet_open',
                    'opens_at': status_payload.get('opens_at'),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not status_payload['is_open']:
            reason = 'đã được giáo viên đóng' if status_payload['is_closed'] else 'đã hết hạn'
            return Response(
                {'detail': f'Bài quiz {reason}, không thể nộp.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return None

    @staticmethod
    def _reject_if_out_of_attempts(assignment, attempt_count):
        """403 Response if the student has exhausted max_attempts for this classroom, else None."""
        if not assignment or not assignment.max_attempts or assignment.max_attempts <= 0:
            return None
        if attempt_count < assignment.max_attempts:
            return None
        return Response(
            {'detail': f'Bạn đã sử dụng hết {assignment.max_attempts} lần làm bài trong lớp này.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def _grade_answers(questions, answers):
        """Score each question against the student's answers. Returns (results, correct_count)."""
        results = []
        correct_count = 0
        for question in questions:
            q_uid = str(question.uid)
            chosen = answers.get(q_uid)
            is_correct = bool(chosen) and chosen == question.correct_answer
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
        return results, correct_count

    @staticmethod
    def _strip_answer_key(results):
        for r in results:
            r.pop('explanation', None)
            r.pop('correct_answer', None)

    def _link_exam_submission(self, quiz_id, classroom_id, student_id, answers, time_taken_seconds):
        """If this quiz is linked to a quiz-type exam in the classroom, record the grade there too."""
        try:
            from features.course.exam.repositories import ExamRepository
            from features.course.exam.services import ExamSubmissionService
            linked_exams = ExamRepository().find_by_ref_id_and_classroom(quiz_id, classroom_id)
            if not linked_exams:
                return
            exam_sub_service = ExamSubmissionService()
            for exam in linked_exams:
                try:
                    exam_sub_service.submit_exam(
                        exam_id=exam.uid,
                        student_id=student_id,
                        data={
                            "submission_type": "online_quiz",
                            "answers": {str(k): str(v) for k, v in answers.items()},
                            "time_taken_seconds": time_taken_seconds,
                        },
                    )
                except ValueError:
                    pass  # already submitted or other domain error — don't break quiz response
        except Exception as exc:
            logger.warning(
                f"[Exam] Exam-linkage side-effect failed for quiz={quiz_id} classroom={classroom_id}: {exc}"
            )

    def _issue_certificates(self, quiz_id, classroom_id, student_id):
        """If this submission completes a QuizCollection, issue its certificate (idempotent)."""
        try:
            from features.quiz_collection.services import CertificateIssuanceService
            from features.quiz_collection.serializers.issued_certificate_response_serializer import (
                IssuedCertificateResponseSerializer,
            )
            newly_issued = CertificateIssuanceService().check_and_issue(
                student_id=student_id,
                classroom_id=classroom_id,
                just_submitted_quiz_id=quiz_id,
            )
            if not newly_issued:
                return []
            enriched = CertificateIssuanceService().enrich_issued_certificates(newly_issued)
            return IssuedCertificateResponseSerializer(enriched, many=True).data
        except Exception as exc:
            logger.exception(
                f"[Certificate] check_and_issue failed student={student_id} "
                f"quiz={quiz_id} classroom={classroom_id}: {exc}"
            )
            return []
