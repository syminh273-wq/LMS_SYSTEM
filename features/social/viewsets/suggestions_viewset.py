"""
User suggestions endpoint.

GET /api/v1/consumer/social/suggestions/   (Consumer auth)
GET /api/v1/space/social/suggestions/      (Space / teacher auth)
  limit  (default 6, max 20)

Returns active accounts (Consumers + Spaces) that the current user is
NOT yet following (excluding self). Profile data is sourced from the
social UserProfile when available.
"""

import uuid

from rest_framework.response import Response
from rest_framework.views import APIView

from core.storages.storage_service import storage_service
from features.account.consumer.repositories import ConsumerRepository
from features.account.space.repositories import Repository as SpaceRepository
from features.social.models import UserFollow
from features.social.repositories.profile_repository import ProfileRepository


def _resolve_avatar(value: str) -> str:
    if not value:
        return ''
    return storage_service.get_public_url(value)


class SuggestedUsersView(APIView):
    """GET /api/v1/{consumer|space}/social/suggestions/"""

    def get(self, request):
        limit = min(int(request.query_params.get('limit', 6)), 20)
        if limit <= 0:
            limit = 6

        current_uid = uuid.UUID(str(request.user.uid))

        try:
            following_rows = list(
                UserFollow.objects.filter(follower_uid=current_uid).limit(500)
            )
            following_uids = {str(f.followed_uid) for f in following_rows}
        except Exception:
            following_uids = set()

        following_uids.add(str(current_uid))

        pool: list[dict] = []

        for s in SpaceRepository().get_active():
            if not s or not s.uid:
                continue
            uid = str(s.uid)
            if uid in following_uids:
                continue
            pool.append({
                'uid': uid,
                'name': s.full_name or s.name or s.slug or '',
                'username': s.slug or '',
                'avatar_raw': s.avatar_url or s.logo_url or '',
                'role': 'teacher',
                'kind': 'space',
            })

        for c in ConsumerRepository().get_active():
            if not c or not c.uid:
                continue
            uid = str(c.uid)
            if uid in following_uids:
                continue
            pool.append({
                'uid': uid,
                'name': c.full_name or c.username or '',
                'username': c.username or '',
                'avatar_raw': c.avatar_url or '',
                'role': getattr(c, 'role', '') or 'student',
                'kind': 'consumer',
            })

        if not pool:
            for s in SpaceRepository().get_active():
                if not s or not s.uid:
                    continue
                uid = str(s.uid)
                if uid == str(current_uid):
                    continue
                pool.append({
                    'uid': uid,
                    'name': s.full_name or s.name or s.slug or '',
                    'username': s.slug or '',
                    'avatar_raw': s.avatar_url or s.logo_url or '',
                    'role': 'teacher',
                    'kind': 'space',
                })
                if len(pool) >= limit:
                    break

        profile_repo = ProfileRepository()
        results = []
        for item in pool[:limit]:
            try:
                profile = profile_repo.get_by_owner(uuid.UUID(item['uid']))
            except Exception:
                profile = None

            results.append({
                'consumer_uid': item['uid'],
                'name': item['name'],
                'username': item['username'],
                'avatar': _resolve_avatar(item['avatar_raw']),
                'role': item['role'],
                'kind': item['kind'],
                'bio': getattr(profile, 'bio', '') or '',
                'major': getattr(profile, 'major', '') or '',
                'department': getattr(profile, 'department', '') or '',
                'followers_count': int(getattr(profile, 'followers_count', 0) or 0),
            })

        return Response({
            'count': len(results),
            'results': results,
        })
