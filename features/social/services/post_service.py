import uuid
from datetime import datetime

from features.social.models import ConsumerPost, PostLike, PostComment
from features.social.services.follow_service import FollowService


class PostService:

    # ── Serialize helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _serialize_post(p: ConsumerPost, liked_by_me: bool = False) -> dict:
        return {
            'uid':            str(p.uid),
            'consumer_uid':   str(p.consumer_uid),
            'author_name':    p.author_name or '',
            'author_avatar':  p.author_avatar or '',
            'content':        p.content or '',
            'emotion':        p.emotion or '',
            'image_url':      p.image_url or '',
            'visibility':     p.visibility or 'public',
            'classroom_tag':  str(p.classroom_tag) if p.classroom_tag else None,
            'likes_count':    int(p.likes_count or 0),
            'comments_count': int(p.comments_count or 0),
            'liked_by_me':    liked_by_me,
            'created_at':     p.created_at.isoformat() if p.created_at else None,
        }

    @staticmethod
    def _serialize_comment(c: PostComment) -> dict:
        return {
            'uid':           str(c.uid),
            'post_uid':      str(c.post_uid),
            'consumer_uid':  str(c.consumer_uid),
            'author_name':   c.author_name or '',
            'author_avatar': c.author_avatar or '',
            'content':       c.content or '',
            'created_at':    c.created_at.isoformat() if c.created_at else None,
        }

    # ── Posts ─────────────────────────────────────────────────────────────────

    def create_post(self, consumer_uid, author_name: str, author_avatar: str, data: dict) -> dict:
        post = ConsumerPost.create(
            consumer_uid=uuid.UUID(str(consumer_uid)),
            author_name=author_name,
            author_avatar=author_avatar,
            content=data.get('content', ''),
            emotion=data.get('emotion', ''),
            image_url=data.get('image_url', ''),
            visibility=data.get('visibility', 'public'),
            classroom_tag=uuid.UUID(str(data['classroom_tag'])) if data.get('classroom_tag') else None,
            created_at=datetime.utcnow(),
        )
        return self._serialize_post(post)

    def get_feed(self, requester_uid, limit: int = 20, before: str | None = None) -> list[dict]:
        """Public feed — all public posts across all users, newest first."""
        qs = ConsumerPost.objects.filter(bucket=0, is_deleted=False)
        if before:
            try:
                qs = qs.filter(created_at__lt=datetime.fromisoformat(before))
            except Exception:
                pass
        posts = list(qs.limit(limit * 2))
        posts = [p for p in posts if p.visibility == 'public'][:limit]

        liked_set = self._liked_set(requester_uid, [p.uid for p in posts])
        return [self._serialize_post(p, str(p.uid) in liked_set) for p in posts]

    def get_following_feed(self, requester_uid, limit: int = 20) -> list[dict]:
        """Feed from people the user is following."""
        following = FollowService().get_following(requester_uid, limit=200)
        followed_uids = [uuid.UUID(f['consumer_uid']) for f in following]
        
        if not followed_uids:
            return []
            
        # We can't easily do a multi-user 'IN' query with Cassandra effectively for a feed
        # So we fetch a few from each or use the global bucket and filter.
        # For simplicity and performance with small following lists, we fetch from the global bucket
        # but filter for the ones we follow.
        
        qs = ConsumerPost.objects.filter(bucket=0, is_deleted=False).limit(limit * 5)
        posts_raw = list(qs)
        
        followed_set = {str(uid) for uid in followed_uids}
        posts = [p for p in posts_raw if str(p.consumer_uid) in followed_set][:limit]
        
        liked_set = self._liked_set(requester_uid, [p.uid for p in posts])
        return [self._serialize_post(p, str(p.uid) in liked_set) for p in posts]

    def get_my_posts(self, consumer_uid, limit: int = 20, before: str | None = None) -> list[dict]:
        """All posts by a specific user (visible to themselves)."""
        qs = ConsumerPost.objects.filter(bucket=0, consumer_uid=uuid.UUID(str(consumer_uid)), is_deleted=False)
        if before:
            try:
                qs = qs.filter(created_at__lt=datetime.fromisoformat(before))
            except Exception:
                pass
        posts = list(qs.limit(limit))
        return [self._serialize_post(p) for p in posts]

    def get_user_posts(self, consumer_uid, requester_uid, limit: int = 20) -> list[dict]:
        """Posts by user visible to requester (filters by visibility)."""
        is_owner = str(consumer_uid) == str(requester_uid)
        posts_raw = list(
            ConsumerPost.objects.filter(bucket=0, consumer_uid=uuid.UUID(str(consumer_uid)), is_deleted=False).limit(limit * 2)
        )
        if is_owner:
            posts = posts_raw[:limit]
        else:
            posts = [p for p in posts_raw if p.visibility == 'public'][:limit]

        liked_set = self._liked_set(requester_uid, [p.uid for p in posts])
        return [self._serialize_post(p, str(p.uid) in liked_set) for p in posts]

    def get_post(self, post_uid: str) -> ConsumerPost | None:
        try:
            results = list(ConsumerPost.objects.filter(bucket=0, uid=uuid.UUID(post_uid)).limit(1))
            return results[0] if results else None
        except Exception:
            return None

    def delete_post(self, post_uid: str, consumer_uid) -> bool:
        post = self.get_post(post_uid)
        if not post or str(post.consumer_uid) != str(consumer_uid):
            return False
        post.update(is_deleted=True)
        return True

    # ── Likes ─────────────────────────────────────────────────────────────────

    def toggle_like(self, post_uid: str, consumer_uid) -> dict:
        p_uid = uuid.UUID(post_uid)
        c_uid = uuid.UUID(str(consumer_uid))
        existing = list(PostLike.objects.filter(post_uid=p_uid, consumer_uid=c_uid).limit(1))

        post = self.get_post(post_uid)
        if not post:
            raise ValueError('Post not found')

        if existing:
            existing[0].delete()
            new_count = max(0, int(post.likes_count or 0) - 1)
            post.update(likes_count=new_count)
            return {'liked': False, 'likes_count': new_count}
        else:
            PostLike.create(post_uid=p_uid, consumer_uid=c_uid)
            new_count = int(post.likes_count or 0) + 1
            post.update(likes_count=new_count)
            return {'liked': True, 'likes_count': new_count}

    def _liked_set(self, consumer_uid, post_uids: list) -> set:
        if not post_uids or not consumer_uid:
            return set()
        result = set()
        c_uid = uuid.UUID(str(consumer_uid))
        for p_uid in post_uids:
            rows = list(PostLike.objects.filter(post_uid=p_uid, consumer_uid=c_uid).limit(1))
            if rows:
                result.add(str(p_uid))
        return result

    # ── Comments ──────────────────────────────────────────────────────────────

    def get_comments(self, post_uid: str, limit: int = 30) -> list[dict]:
        comments = list(
            PostComment.objects.filter(post_uid=uuid.UUID(post_uid), is_deleted=False).limit(limit)
        )
        return [self._serialize_comment(c) for c in comments]

    def add_comment(self, post_uid: str, consumer_uid, author_name: str, author_avatar: str, content: str) -> dict:
        p_uid = uuid.UUID(post_uid)
        comment = PostComment.create(
            post_uid=p_uid,
            consumer_uid=uuid.UUID(str(consumer_uid)),
            author_name=author_name,
            author_avatar=author_avatar,
            content=content,
            created_at=datetime.utcnow(),
        )
        # Increment comments count
        post = self.get_post(post_uid)
        if post:
            post.update(comments_count=int(post.comments_count or 0) + 1)
        return self._serialize_comment(comment)

    def delete_comment(self, post_uid: str, comment_uid: str, consumer_uid) -> bool:
        try:
            rows = list(
                PostComment.objects.filter(post_uid=uuid.UUID(post_uid), uid=uuid.UUID(comment_uid)).limit(1)
            )
            if not rows:
                return False
            c = rows[0]
            if str(c.consumer_uid) != str(consumer_uid):
                return False
            c.update(is_deleted=True)
            post = self.get_post(post_uid)
            if post:
                post.update(comments_count=max(0, int(post.comments_count or 0) - 1))
            return True
        except Exception:
            return False
