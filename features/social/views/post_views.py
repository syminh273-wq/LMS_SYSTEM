from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from features.account.consumer.models import Consumer
from features.account.space.models import Space
from features.social.services import PostService
from features.social.services.profile_service import ProfileService


def _resolve_avatar_url(value: str) -> str:
    if not value:
        return ''
    from core.storages.storage_service import storage_service
    return storage_service.get_public_url(value)


def _profile_avatar(user) -> str:
    try:
        owner_type = 'space' if isinstance(user, Space) else 'consumer'
        profile = ProfileService().get_or_create_for_user(user)
        return (profile.avatar_url or '') if profile else ''
    except Exception:
        return ''


def _author_info(user):
    name = getattr(user, 'full_name', '') or getattr(user, 'username', '') or ''
    raw_avatar = getattr(user, 'avatar_url', '') or ''
    if not raw_avatar:
        raw_avatar = _profile_avatar(user)
    return name, _resolve_avatar_url(raw_avatar)


def _detect_owner_type(user) -> str:
    cls_name = type(user).__name__
    if cls_name == 'Space':
        return 'space'
    return 'consumer'


class FeedView(APIView):
    """GET /api/v1/consumer/social/feed/"""

    def get(self, request):
        before = request.query_params.get('before')
        limit  = min(int(request.query_params.get('limit', 20)), 50)
        posts  = PostService().get_feed(request.user.uid, limit=limit, before=before)
        return Response(posts)


class FollowingFeedView(APIView):
    """GET /api/v1/consumer/social/feed/following/"""

    def get(self, request):
        limit = min(int(request.query_params.get('limit', 20)), 50)
        posts = PostService().get_following_feed(request.user.uid, limit=limit)
        return Response(posts)


class MyPostsView(APIView):
    """GET /api/v1/consumer/social/posts/mine/"""

    def get(self, request):
        before = request.query_params.get('before')
        limit  = min(int(request.query_params.get('limit', 20)), 50)
        posts  = PostService().get_my_posts(request.user.uid, limit=limit, before=before)
        return Response(posts)


class UserPostsView(APIView):
    """GET /api/v1/consumer/social/posts/user/<owner_id>/"""

    def get(self, request, owner_id=None):
        limit = min(int(request.query_params.get('limit', 20)), 50)
        posts = PostService().get_user_posts(owner_id, request.user.uid, limit=limit)
        return Response(posts)


class PostListCreateView(APIView):
    """POST /api/v1/consumer/social/posts/   — create post"""

    def post(self, request):
        content   = (request.data.get('content') or '').strip()
        emotion   = request.data.get('emotion', '')
        image_url = request.data.get('image_url', '')
        image_urls = request.data.get('image_urls', [])
        visibility = request.data.get('visibility', 'public')
        classroom_tags = request.data.get('classroom_tags') or request.data.get('classroom_tag') or []

        if not content and not image_url and not image_urls:
            return Response({'error': 'Nội dung không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        if visibility not in ('public', 'private', 'friends'):
            return Response({'error': 'visibility không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)

        name, avatar = _author_info(request.user)
        owner_type = _detect_owner_type(request.user)
        space_uid = request.user.uid if owner_type == 'space' else None
        post = PostService().create_post(
            owner_id=request.user.uid,
            owner_name=name,
            owner_avatar=avatar,
            data={
                'content': content,
                'emotion': emotion,
                'image_url': image_url,
                'image_urls': image_urls,
                'visibility': visibility,
                'classroom_tags': classroom_tags,
            },
            owner_type=owner_type,
            space_uid=space_uid,
        )
        return Response(post, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """GET / DELETE /api/v1/consumer/social/posts/<uid>/"""

    def get(self, request, uid=None):
        svc = PostService()
        post = svc.get_post(uid)
        if not post or post.is_deleted:
            return Response({'error': 'Không tìm thấy bài đăng'}, status=status.HTTP_404_NOT_FOUND)
        profile_avatars = svc._profile_avatar_map([post.owner_id])
        return Response(svc._serialize_post(post, profile_avatars=profile_avatars))

    def delete(self, request, uid=None):
        ok = PostService().delete_post(uid, request.user.uid)
        if not ok:
            return Response({'error': 'Không thể xóa bài đăng'}, status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    """POST /api/v1/consumer/social/posts/<uid>/like/"""

    def post(self, request, uid=None):
        try:
            result = PostService().toggle_like(uid, request.user.uid)
            return Response(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


class PostCommentView(APIView):
    """GET/POST /api/v1/consumer/social/posts/<uid>/comments/"""

    def get(self, request, uid=None):
        limit    = min(int(request.query_params.get('limit', 30)), 100)
        comments = PostService().get_comments(uid, limit=limit)
        return Response(comments)

    def post(self, request, uid=None):
        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'error': 'Nội dung bình luận không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        name, avatar = _author_info(request.user)
        owner_type = _detect_owner_type(request.user)
        comment = PostService().add_comment(uid, request.user.uid, name, avatar, content, owner_type=owner_type)
        return Response(comment, status=status.HTTP_201_CREATED)


class PostCommentDeleteView(APIView):
    """DELETE /api/v1/consumer/social/posts/<uid>/comments/<cuid>/"""

    def delete(self, request, uid=None, cuid=None):
        ok = PostService().delete_comment(uid, cuid, request.user.uid)
        if not ok:
            return Response({'error': 'Không thể xóa bình luận'}, status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)
