from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from features.social.services import FollowService
from features.account.consumer.models import Consumer
import uuid


def _user_info(u_uid):
    try:
        user = Consumer.objects.get(uid=uuid.UUID(str(u_uid)))
        return {
            'name': user.full_name or user.username or '',
            'avatar': user.avatar_url or ''
        }
    except Exception:
        return {'name': 'Unknown', 'avatar': ''}


class FollowToggleView(APIView):
    """POST /api/v1/consumer/social/follow/<target_uid>/"""

    def post(self, request, target_uid=None):
        if str(request.user.uid) == str(target_uid):
            return Response({'error': 'Bạn không thể follow chính mình'}, status=status.HTTP_400_BAD_REQUEST)
            
        service = FollowService()
        is_following = service.is_following(request.user.uid, target_uid)
        
        if is_following:
            service.unfollow_user(request.user.uid, target_uid)
            return Response({'following': False})
        else:
            # Get info for both to store snapshots
            follower_data = {
                'name': getattr(request.user, 'full_name', '') or getattr(request.user, 'username', '') or '',
                'avatar': getattr(request.user, 'avatar_url', '') or ''
            }
            followed_data = _user_info(target_uid)
            
            service.follow_user(request.user.uid, target_uid, follower_data, followed_data)
            return Response({'following': True})


class FollowingListView(APIView):
    """GET /api/v1/consumer/social/following/ (optional ?uid=)"""

    def get(self, request):
        user_uid = request.query_params.get('uid') or request.user.uid
        limit = min(int(request.query_params.get('limit', 50)), 100)
        following = FollowService().get_following(user_uid, limit=limit)
        return Response(following)


class FollowersListView(APIView):
    """GET /api/v1/consumer/social/followers/ (optional ?uid=)"""

    def get(self, request):
        user_uid = request.query_params.get('uid') or request.user.uid
        limit = min(int(request.query_params.get('limit', 50)), 100)
        followers = FollowService().get_followers(user_uid, limit=limit)
        return Response(followers)


class FollowStatusView(APIView):
    """GET /api/v1/consumer/social/follow/status/<target_uid>/"""

    def get(self, request, target_uid=None):
        is_following = FollowService().is_following(request.user.uid, target_uid)
        return Response({'following': is_following})
