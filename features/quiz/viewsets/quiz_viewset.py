import json

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views.api.base_viewset import BaseModelViewSet
from features.quiz.serializers.quiz_request_serializer import (
    QuizGenerateRequestSerializer,
    QuizUpdateRequestSerializer,
    QuizAssignRequestSerializer,
    QuizAssignUpdateRequestSerializer,
    QuizQuestionUpdateRequestSerializer,
)
from features.quiz.serializers.quiz_response_serializer import (
    QuizResponseSerializer,
    QuizDetailResponseSerializer,
    QuizAssignmentResponseSerializer,
    QuizAttemptResponseSerializer,
    QuizQuestionSerializer,
)
from features.quiz.services.quiz_service import QuizService
from features.quiz.services.quiz_generation_service import QuizGenerationService, QUIZ_TYPES, _extract_pdf_text


class QuizViewSet(BaseModelViewSet):
    serializer_class = QuizResponseSerializer
    service = QuizService()
    generation_service = QuizGenerationService()

    def get_queryset(self):
        classroom_id = self.request.query_params.get('classroom_id')
        if classroom_id:
            return self.service.get_by_classroom(classroom_id)
        return self.service.get_by_teacher(self.request.user.uid)

    # ── LIST  GET /quizzes/ ────────────────────────────────────────────────
    def list(self, request, *args, **kwargs):
        queryset = list(self.get_queryset())
        return Response(QuizResponseSerializer(queryset, many=True).data)

    # ── RETRIEVE  GET /quizzes/<uid>/ ─────────────────────────────────────
    def retrieve(self, request, *args, **kwargs):
        quiz, questions = self.service.get_with_questions(kwargs['uid'])
        assignments = self.service.get_assigned_classrooms(kwargs['uid'])
        data = QuizDetailResponseSerializer({
            **{f: getattr(quiz, f) for f in [
                'uid', 'created_by', 'resource_id',
                'title', 'description', 'questions_count', 'status',
                'created_at', 'updated_at',
            ]},
            'questions': questions,
        }).data
        data['assigned_classrooms'] = QuizAssignmentResponseSerializer(assignments, many=True).data
        return Response(data)

    # ── QUIZ TYPES  GET /quizzes/types/ ───────────────────────────────────
    @action(detail=False, methods=['get'], url_path='types')
    def types(self, request):
        labels = {
            'multiple_choice': 'Trắc nghiệm 4 đáp án',
            'true_false':      'Đúng / Sai',
            'fill_blank':      'Điền vào chỗ trống',
            'scenario':        'Tình huống thực tế',
        }
        return Response([{'value': t, 'label': labels.get(t, t)} for t in QUIZ_TYPES])

    # ── GENERATE SYNC  POST /quizzes/generate/ ────────────────────────────
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        req_serializer = QuizGenerateRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        params = req_serializer.validated_data

        resource_id = params.get('resource_id')
        content     = params.get('content')
        quiz_type   = params.get('quiz_type', 'multiple_choice')
        num_questions     = params.get('num_questions', 10)
        max_content_length = params.get('max_content_length', 12000)
        resource_url = None

        uploaded_file = request.FILES.get('file')
        if uploaded_file and not content and not resource_id:
            try:
                content = _extract_pdf_text(uploaded_file.read())
            except Exception as exc:
                return Response({'detail': f'Không thể đọc file PDF: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        if not content and not resource_id:
            return Response({'detail': "Provide 'content', 'resource_id', or upload a 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        if resource_id and not content:
            from features.resource.repositories.resource_repository import ResourceRepository
            resource = ResourceRepository().find(resource_id)
            resource_url = resource.url

        try:
            ai_data = QuizGenerationService.generate(
                content=content, resource_url=resource_url,
                quiz_type=quiz_type, num_questions=num_questions,
                max_content_length=max_content_length,
            )
        except Exception as exc:
            return Response({'detail': f'AI generation failed: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

        quiz, questions = self.service.create_quiz_with_questions(
            created_by=request.user.uid,
            title=ai_data.get('title', 'Untitled Quiz'),
            description=ai_data.get('description', ''),
            resource_id=resource_id,
            questions=ai_data['questions'],
        )

        data = QuizDetailResponseSerializer({
            **{f: getattr(quiz, f) for f in [
                'uid', 'created_by', 'resource_id',
                'title', 'description', 'questions_count', 'status',
                'created_at', 'updated_at',
            ]},
            'questions': questions,
        }).data
        data['assigned_classrooms'] = []
        return Response(data, status=status.HTTP_201_CREATED)

    # ── GENERATE STREAM  POST /quizzes/generate-stream/ ───────────────────
    @action(detail=False, methods=['post'], url_path='generate-stream')
    def generate_stream(self, request):
        req_serializer = QuizGenerateRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        params = req_serializer.validated_data

        resource_id = params.get('resource_id')
        content     = params.get('content')
        quiz_type   = params.get('quiz_type', 'multiple_choice')
        num_questions     = params.get('num_questions', 10)
        max_content_length = params.get('max_content_length', 12000)
        resource_url = None

        uploaded_file = request.FILES.get('file')
        if uploaded_file and not content and not resource_id:
            try:
                content = _extract_pdf_text(uploaded_file.read())
            except Exception as exc:
                err_msg = json.dumps({'type': 'error', 'detail': f'Không thể đọc file PDF: {exc}'})
                def err_stream():
                    yield f"data: {err_msg}\n\n"
                response = StreamingHttpResponse(err_stream(), content_type='text/event-stream')
                response['Cache-Control'] = 'no-cache'
                return response

        if not content and not resource_id:
            msg = json.dumps({'type': 'error', 'detail': "Provide 'content', 'resource_id', or upload a 'file'."})
            def missing_stream():
                yield f"data: {msg}\n\n"
            response = StreamingHttpResponse(missing_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            return response

        if resource_id and not content:
            from features.resource.repositories.resource_repository import ResourceRepository
            resource = ResourceRepository().find(resource_id)
            resource_url = resource.url

        teacher_uid = request.user.uid
        service = self.service

        def event_stream():
            quiz = None
            total = 0
            try:
                for event in QuizGenerationService.generate_stream(
                    content=content, resource_url=resource_url,
                    quiz_type=quiz_type, num_questions=num_questions,
                    max_content_length=max_content_length,
                ):
                    if event['type'] == 'error':
                        yield f"data: {json.dumps(event)}\n\n"
                        return

                    if event['type'] == 'meta':
                        quiz = service.create_quiz_shell(
                            created_by=teacher_uid,
                            title=event['title'],
                            description=event['description'],
                            resource_id=resource_id,
                        )
                        yield f"data: {json.dumps({'type': 'meta', 'quiz_uid': str(quiz.uid), 'title': event['title'], 'description': event['description']})}\n\n"

                    elif event['type'] == 'question' and quiz:
                        q = service.add_question(quiz, event, event['index'])
                        yield f"data: {json.dumps({'type': 'question', 'index': event['index'], 'question_uid': str(q.uid), 'question': event['question'], 'options': event['options'], 'correct': event['correct'], 'explanation': event['explanation']})}\n\n"
                        total = event['index'] + 1

                    elif event['type'] == 'done':
                        if quiz:
                            service.finalize_quiz(quiz, total)
                        yield f"data: {json.dumps({'type': 'done', 'total': total, 'quiz_uid': str(quiz.uid) if quiz else None})}\n\n"

            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    # ── ASSIGN  POST /quizzes/<uid>/assign/ ───────────────────────────────
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, uid=None):
        serializer = QuizAssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        classroom_id = d.pop('classroom_id')
        assignment = self.service.assign_to_classroom(
            quiz_uid=uid,
            classroom_id=classroom_id,
            assigned_by=request.user.uid,
            **d
        )
        return Response(QuizAssignmentResponseSerializer(assignment).data, status=status.HTTP_201_CREATED)

    # ── UPDATE ASSIGNMENT  PATCH /quizzes/<uid>/assign/<classroom_id>/ ────
    @action(detail=True, methods=['patch'], url_path=r'assign/(?P<classroom_id>[^/.]+)')
    def update_assignment(self, request, uid=None, classroom_id=None):
        serializer = QuizAssignUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = self.service.update_assignment_settings(
            uid, classroom_id, **serializer.validated_data
        )
        return Response(QuizAssignmentResponseSerializer(assignment).data)

    # ── UNASSIGN  DELETE /quizzes/<uid>/assign/<classroom_id>/ ────────────
    @action(detail=True, methods=['delete'], url_path=r'unassign/(?P<classroom_id>[^/.]+)')
    def unassign(self, request, uid=None, classroom_id=None):
        self.service.unassign_from_classroom(quiz_uid=uid, classroom_id=classroom_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── ATTEMPTS  GET /quizzes/<uid>/attempts/?classroom_id=<id> ──────────
    @action(detail=True, methods=['get'], url_path='attempts')
    def attempts(self, request, **kwargs):
        classroom_id = request.query_params.get('classroom_id')
        if not classroom_id:
            return Response({'detail': 'classroom_id is required.'}, status=400)
        attempts = self.service.get_all_attempts(kwargs['uid'], classroom_id)
        return Response(QuizAttemptResponseSerializer(list(attempts), many=True).data)

    # ── UPDATE QUESTION  PATCH /quizzes/<uid>/questions/<question_uid>/ ──────
    @action(detail=True, methods=['patch'], url_path=r'questions/(?P<question_uid>[^/.]+)')
    def update_question(self, request, uid=None, question_uid=None):
        quiz = self.service.find(uid)
        if str(quiz.created_by) != str(request.user.uid):
            return Response({'detail': 'You do not have permission to edit this quiz.'}, status=status.HTTP_403_FORBIDDEN)
        if quiz.status != 'draft':
            return Response({'detail': 'Questions can only be edited while the quiz is in draft status.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = QuizQuestionUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            return Response({'detail': 'No fields provided to update.'}, status=status.HTTP_400_BAD_REQUEST)

        question = self.service.find_question(quiz.uid, question_uid)
        updated = self.service.update_question(question, **serializer.validated_data)
        return Response(QuizQuestionSerializer(updated).data)

    # ── UPDATE  PATCH /quizzes/<uid>/ ─────────────────────────────────────
    def partial_update(self, request, *args, **kwargs):
        quiz = self.service.find(kwargs['uid'])
        serializer = QuizUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = self.service.update(quiz, **serializer.validated_data)
        return Response(QuizResponseSerializer(updated).data)

    # ── DELETE  DELETE /quizzes/<uid>/ ────────────────────────────────────
    def destroy(self, request, *args, **kwargs):
        self.service.delete_quiz(kwargs['uid'])
        return Response(status=status.HTTP_204_NO_CONTENT)
