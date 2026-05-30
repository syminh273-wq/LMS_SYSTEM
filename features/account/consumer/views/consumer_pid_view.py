from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.search_engine.typesense.service import TypesenseService


class ConsumerByPidView(APIView):
    """GET /api/v1/consumer/account/by-pid/<pid>/"""

    def get(self, request, pid: str):
        svc = TypesenseService()
        try:
            resp = svc.search(
                collection='lms_consumer',
                query='*',
                query_by=['pid'],
                filter_by=f'pid:={pid} && is_deleted:false',
                limit=1,
            )
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not resp.results:
            return Response({'detail': 'Consumer not found.'}, status=status.HTTP_404_NOT_FOUND)

        hit = resp.results[0]
        return Response({
            'uid':        hit.id,
            'pid':        hit.extra.get('pid', ''),
            'username':   hit.extra.get('username', ''),
            'email':      hit.extra.get('email', ''),
            'full_name':  hit.extra.get('full_name', ''),
            'phone':      hit.extra.get('phone', ''),
            'role':       hit.extra.get('role', ''),
            'is_active':  hit.extra.get('is_active', True),
            'created_at': hit.extra.get('created_at'),
        })
