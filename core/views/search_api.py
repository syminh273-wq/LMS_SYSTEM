"""
LMS Typesense Search API

Endpoints:
  GET /api/v1/space/search/          — teacher: search classrooms, exams, quizzes, consumers
  GET /api/v1/space/search/health/   — health check

Query params (space search):
  q           (required) search query
  types       classroom,exam,quiz,consumer  (default: all)
  classroom_id  filter exams by classroom
  limit       (default 10, max 50)
  offset      (default 0)
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from core.search_engine.typesense.service import TypesenseService
from core.views.mixins import UserScopeMixin


class SpaceSearchAPIView(UserScopeMixin, APIView):
    """
    GET /api/v1/space/search/?q=<query>&types=classroom,exam,quiz,consumer
    Authenticated: Space (teacher) accounts only.
    """

    SUPPORTED_TYPES = ('classroom', 'exam', 'quiz', 'consumer')

    _COLLECTION_CONFIG = {
        'classroom': {
            'collection':  'lms_classroom',
            'query_by':    ['name', 'pid', 'description'],
        },
        'exam': {
            'collection':  'lms_exam',
            'query_by':    ['title', 'description', 'body'],
        },
        'quiz': {
            'collection':  'lms_quiz',
            'query_by':    ['title', 'description'],
        },
        'consumer': {
            'collection':  'lms_consumer',
            'query_by':    ['full_name', 'email', 'username', 'phone'],
        },
    }

    def get(self, request):
        query = (request.query_params.get('q') or '').strip()
        if not query:
            return Response({'error': 'q is required'}, status=400)

        raw_types = request.query_params.get('types', '')
        types = [t.strip() for t in raw_types.split(',') if t.strip()] or list(self.SUPPORTED_TYPES)
        types = [t for t in types if t in self.SUPPORTED_TYPES]

        limit  = min(int(request.query_params.get('limit',  10)), 50)
        offset = max(int(request.query_params.get('offset',  0)),  0)
        classroom_id = request.query_params.get('classroom_id', '')

        svc = TypesenseService()
        output = {}

        for type_key in types:
            cfg = self._COLLECTION_CONFIG[type_key]
            filter_parts = ['is_deleted:false']

            # Teacher sees only their own classrooms/exams/quizzes
            if type_key in ('classroom', 'exam') and hasattr(request.user, 'uid'):
                filter_parts.append(f'teacher_id:{request.user.uid}')
            if type_key == 'quiz' and hasattr(request.user, 'uid'):
                filter_parts.append(f'created_by:{request.user.uid}')
            if type_key == 'exam' and classroom_id:
                filter_parts.append(f'classroom_id:{classroom_id}')

            try:
                resp = svc.search(
                    collection=cfg['collection'],
                    query=query,
                    query_by=cfg['query_by'],
                    filter_by=' && '.join(filter_parts),
                    limit=limit,
                    offset=offset,
                )
                output[type_key] = resp.to_dict()
            except Exception as exc:
                output[type_key] = {'total_hits': 0, 'results': [], 'error': str(exc)}

        return Response(output)


class SearchHealthAPIView(APIView):
    """GET /api/v1/space/search/health/"""

    def get(self, request):
        healthy = TypesenseService().health()
        return Response(
            {'status': 'ok' if healthy else 'unavailable'},
            status=200 if healthy else 503,
        )
