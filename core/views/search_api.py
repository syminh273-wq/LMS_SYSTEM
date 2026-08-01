from rest_framework.response import Response
from rest_framework.views import APIView

from core.search_engine.typesense.service import TypesenseService
from core.views.mixins import SpaceScopeMixin


class SpaceSearchAPIView(SpaceScopeMixin, APIView):
    """
    GET /api/v1/space/search/?q=<query>&types=classroom,exam,quiz,consumer
    Authenticated: Space (teacher) accounts only.
    """

    SUPPORTED_TYPES = ('classroom', 'exam', 'quiz', 'consumer', 'resource')

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
        # Use lms_consumer for full-text search; filter by uid IN (...) from TeacherContact.
        'consumer': {
            'collection':  'lms_consumer',
            'query_by':    ['full_name', 'first_name', 'last_name', 'email', 'username'],
        },
        'resource': {
            'collection':  'lms_resource',
            'query_by':    ['name'],
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

            # Teacher sees only their own data
            if type_key in ('classroom', 'exam') and hasattr(request.user, 'uid'):
                filter_parts.append(f'teacher_id:{request.user.uid}')
            if type_key == 'quiz' and hasattr(request.user, 'uid'):
                filter_parts.append(f'created_by:{request.user.uid}')
            if type_key == 'exam' and classroom_id:
                filter_parts.append(f'classroom_id:{classroom_id}')
            if type_key == 'resource' and hasattr(request.user, 'uid'):
                filter_parts.append(f'owner_id:{request.user.uid}')
            # Consumer search: scope to students who have ever studied with this teacher.
            if type_key == 'consumer' and hasattr(request.user, 'uid'):
                from features.course.classroom.repositories.teacher_contact_repository import TeacherContactRepository
                contacts = TeacherContactRepository().get_by_teacher(request.user.uid)
                uids = [str(c.consumer_uid) for c in contacts]
                if not uids:
                    output[type_key] = {'total_hits': 0, 'results': []}
                    continue
                filter_parts = [f'uid:{"[" + ",".join(uids) + "]"}']

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
