"""
Consumer search endpoint.

GET /api/v1/consumer/account/search/
  q        (required) search query
  types    classroom,exam,resource  (default: all)
  limit    (default 10, max 50)
  offset   (default 0)
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from core.search_engine.typesense.service import TypesenseService
from core.views.mixins import UserScopeMixin


class ConsumerSearchAPIView(UserScopeMixin, APIView):
    """Search endpoint for students (consumer accounts)."""

    SUPPORTED_TYPES = ('classroom', 'exam', 'resource')

    _COLLECTION_CONFIG = {
        'classroom': {
            'collection': 'lms_classroom',
            'query_by':   ['name', 'pid', 'description'],
        },
        'exam': {
            'collection': 'lms_exam',
            'query_by':   ['title', 'description'],
        },
        'resource': {
            'collection': 'lms_resource',
            'query_by':   ['name'],
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

        svc = TypesenseService()
        output = {}

        for type_key in types:
            cfg = self._COLLECTION_CONFIG[type_key]
            filter_parts = ['is_deleted:false']

            if type_key == 'classroom':
                filter_parts.append('status:active')
            if type_key == 'exam':
                filter_parts.append('status:published')
            if type_key == 'resource' and hasattr(request.user, 'uid'):
                filter_parts.append(f'owner_id:{request.user.uid}')

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
