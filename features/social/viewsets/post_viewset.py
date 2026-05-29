from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from features.social.services import PostService


def _author_info(user):
    return (
        getattr(user, 'full_name', '') or getattr(user, 'username', '') or '',
        getattr(user, 'avatar_url', '') or '',
    )


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
    """GET /api/v1/consumer/social/posts/user/<consumer_uid>/"""

    def get(self, request, consumer_uid=None):
        limit = min(int(request.query_params.get('limit', 20)), 50)
        posts = PostService().get_user_posts(consumer_uid, request.user.uid, limit=limit)
        return Response(posts)


class PostListCreateView(APIView):
    """
    POST /api/v1/consumer/social/posts/   — create post
    """

    def post(self, request):
        content   = (request.data.get('content') or '').strip()
        emotion   = request.data.get('emotion', '')
        image_url = request.data.get('image_url', '')
        visibility = request.data.get('visibility', 'public')
        classroom_tag = request.data.get('classroom_tag')

        if not content and not image_url:
            return Response({'error': 'Nội dung không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        if visibility not in ('public', 'private', 'friends'):
            return Response({'error': 'visibility không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)

        name, avatar = _author_info(request.user)
        post = PostService().create_post(
            consumer_uid=request.user.uid,
            author_name=name,
            author_avatar=avatar,
            data={
                'content': content,
                'emotion': emotion,
                'image_url': image_url,
                'visibility': visibility,
                'classroom_tag': classroom_tag,
            },
        )
        return Response(post, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """GET / DELETE /api/v1/consumer/social/posts/<uid>/"""

    def get(self, request, uid=None):
        post = PostService().get_post(uid)
        if not post or post.is_deleted:
            return Response({'error': 'Không tìm thấy bài đăng'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PostService()._serialize_post(post))

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
    """
    GET  /api/v1/consumer/social/posts/<uid>/comments/
    POST /api/v1/consumer/social/posts/<uid>/comments/
    """

    def get(self, request, uid=None):
        limit    = min(int(request.query_params.get('limit', 30)), 100)
        comments = PostService().get_comments(uid, limit=limit)
        return Response(comments)

    def post(self, request, uid=None):
        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'error': 'Nội dung bình luận không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        name, avatar = _author_info(request.user)
        comment = PostService().add_comment(uid, request.user.uid, name, avatar, content)
        return Response(comment, status=status.HTTP_201_CREATED)


class PostCommentDeleteView(APIView):
    """DELETE /api/v1/consumer/social/posts/<uid>/comments/<cuid>/"""

    def delete(self, request, uid=None, cuid=None):
        ok = PostService().delete_comment(uid, cuid, request.user.uid)
        if not ok:
            return Response({'error': 'Không thể xóa bình luận'}, status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)
