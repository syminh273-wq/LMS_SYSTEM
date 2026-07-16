import json
import uuid

import django_rq
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rq.job import Job, JobStatus

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
from features.quiz.tasks.generate_quiz_task import generate_quiz_task
from features.quiz.tasks.serializers import (
    QuizGenerateTaskResponseSerializer,
    QuizTaskStatusResponseSerializer,
)
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService


class QuizViewSet(BaseModelViewSet):
    serializer_class = QuizResponseSerializer
    service = QuizService()
    generation_service = QuizGenerationService()

    def get_queryset(self):
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
        try:
            quiz_title = self.service.get_quiz(uid).title
        except Exception:
            quiz_title = ''
        ClassroomActivityLogService().log(
            classroom_uid=classroom_id,
            log_level='major',
            event_type='quiz_assigned',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_id=uid,
            target_name=quiz_title,
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

    # ── GENERATE TASK  POST /quizzes/generate-task/ ──────────────────────────
    @action(detail=False, methods=['post'], url_path='generate-task')
    def generate_task(self, request):
        req_serializer = QuizGenerateRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        params = req_serializer.validated_data

        resource_id = params.get('resource_id')
        content = params.get('content')
        quiz_type = params.get('quiz_type', 'multiple_choice')
        num_questions = params.get('num_questions', 10)
        max_content_length = params.get('max_content_length', 12000)

        uploaded_file = request.FILES.get('file')
        if uploaded_file and not content and not resource_id:
            try:
                content = _extract_pdf_text(uploaded_file.read())
            except Exception as exc:
                return Response(
                    {'detail': f'Không thể đọc file PDF: {exc}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not content and not resource_id:
            return Response(
                {'detail': "Provide 'content', 'resource_id', or upload a 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resource_url = None
        if resource_id and not content:
            from features.resource.repositories.resource_repository import ResourceRepository
            resource = ResourceRepository().find(resource_id)
            resource_url = resource.url

        queue = django_rq.get_queue('default')
        job = queue.enqueue(
            generate_quiz_task,
            teacher_uid=str(request.user.uid),
            content=content,
            resource_url=resource_url,
            quiz_type=quiz_type,
            num_questions=num_questions,
            max_content_length=max_content_length,
            job_id=str(uuid.uuid4()),
            job_timeout=300,
        )
        job.meta['teacher_uid'] = str(request.user.uid)
        job.meta['kind'] = 'generate'
        job.meta['title'] = params.get('title') or 'Tạo Quiz bằng AI'
        job.meta['total_steps'] = num_questions
        job.meta['current_step'] = 0
        job.meta['progress'] = 0
        job.meta['quiz_uid'] = None
        job.meta['error_message'] = None
        job.meta['created_at'] = job.enqueued_at.isoformat() if job.enqueued_at else None
        job.save_meta()

        data = QuizGenerateTaskResponseSerializer({
            'task_id': job.id,
            'status': 'queued',
        }).data
        return Response(data, status=status.HTTP_202_ACCEPTED)

    # ── TASK STATUS  GET /quizzes/tasks/<task_id>/ ──────────────────────────
    RQ_STATUS_MAP = {
        JobStatus.QUEUED: 'queued',
        JobStatus.STARTED: 'running',
        JobStatus.FINISHED: 'successful',
        JobStatus.FAILED: 'failed',
        JobStatus.DEFERRED: 'queued',
        JobStatus.SCHEDULED: 'queued',
        JobStatus.STOPPED: 'failed',
        JobStatus.CANCELED: 'failed',
    }

    def _build_task_item(self, job):
        from features.quiz.tasks.serializers import QuizTaskListItemSerializer
        meta = job.meta or {}
        rq_status = job.get_status()
        mapped = self.RQ_STATUS_MAP.get(rq_status, 'queued')
        frontend_status = 'completed' if mapped == 'successful' else mapped

        quiz_uid = meta.get('quiz_uid')
        error_message = meta.get('error_message')

        if frontend_status == 'completed' and not quiz_uid:
            result = job.result
            if isinstance(result, dict):
                quiz_uid = result.get('quiz_uid') or quiz_uid

        if frontend_status == 'failed' and not error_message:
            exc = job.exc_info
            if exc:
                lines = [l.strip() for l in exc.strip().splitlines() if l.strip()]
                error_message = lines[-1] if lines else 'Task failed without exception info.'
            else:
                error_message = 'Task failed without exception info.'

        if frontend_status == 'completed':
            progress = 100
            current_step = meta.get('total_steps') or 0
        elif frontend_status == 'failed':
            progress = meta.get('progress') or 0
            current_step = meta.get('current_step') or 0
        else:
            progress = meta.get('progress') or 0
            current_step = meta.get('current_step') or 0

        enqueued = job.enqueued_at
        started = job.started_at
        ended = job.ended_at
        return QuizTaskListItemSerializer({
            'id': job.id,
            'kind': meta.get('kind') or 'generate',
            'title': meta.get('title') or 'Tạo Quiz bằng AI',
            'status': frontend_status,
            'progress': progress,
            'current_step': current_step,
            'total_steps': meta.get('total_steps') or 0,
            'quiz_uid': quiz_uid,
            'error_message': error_message,
            'created_at': meta.get('created_at') or (enqueued.isoformat() if enqueued else ''),
            'updated_at': (ended or started or enqueued).isoformat() if (ended or started or enqueued) else '',
            'completed_at': ended.isoformat() if (ended and frontend_status in ('completed', 'failed')) else None,
        }).data

    @action(detail=False, methods=['get'], url_path=r'tasks/(?P<task_id>[^/.]+)')
    def task_status(self, request, task_id=None):
        queue = django_rq.get_queue('default')
        try:
            job = Job.fetch(task_id, connection=queue.connection)
        except Exception:
            return Response(
                {'detail': f'Task "{task_id}" not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        mapped = self.RQ_STATUS_MAP.get(job.get_status(), 'queued')

        result = None
        error = None
        if mapped == 'successful' and job.result is not None:
            result = job.result
        if mapped == 'failed':
            error = job.exc_info or 'Task failed without exception info.'

        data = QuizTaskStatusResponseSerializer({
            'task_id': task_id,
            'status': mapped,
            'result': result,
            'error': error,
        }).data
        return Response(data)

    # ── LIST TASKS  GET /quizzes/tasks/ ──────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='tasks')
    def list_tasks(self, request):
        queue = django_rq.get_queue('default')
        teacher_uid = str(request.user.uid)
        status_filter = request.query_params.get('status')
        if status_filter:
            status_filter = {s.strip() for s in status_filter.split(',') if s.strip()}

        job_ids = list(queue.job_ids)
        started_registry = queue.started_job_registry
        finished_registry = queue.finished_job_registry
        failed_registry = queue.failed_job_registry
        deferred_registry = queue.deferred_job_registry
        scheduled_registry = queue.scheduled_job_registry
        canceled_registry = queue.canceled_job_registry

        all_ids = set(job_ids)
        for reg in (started_registry, finished_registry, failed_registry,
                    deferred_registry, scheduled_registry, canceled_registry):
            try:
                all_ids.update(reg.get_job_ids())
            except Exception:
                continue

        items = []
        for jid in all_ids:
            try:
                job = Job.fetch(jid, connection=queue.connection)
            except Exception:
                continue
            meta = job.meta or {}

            owner_uid = meta.get('teacher_uid')
            if not owner_uid:
                args = job.args or ()
                if args and isinstance(args[0], str) and len(args[0]) >= 8:
                    owner_uid = args[0]
            if owner_uid != teacher_uid:
                continue

            item = self._build_task_item(job)
            if status_filter and item['status'] not in status_filter:
                continue
            items.append(item)

        items.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        return Response(items)
