import os
import uuid
from datetime import datetime

from core.storages.storage_service import storage_service
from features.social.models import ConsumerPost, PostLike, PostComment
from features.social.services.follow_service import FollowService
from features.social.services.profile_service import ProfileService


class PostService:

    # ── Serialize helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _coerce_image_urls(data: dict) -> list[str]:
        """Normalize image URLs from request: accept 'image_urls' (list or JSON string)
        and 'image_url' (single string). Returns deduped list preserving order, with
        image_url inserted at the front if not already present."""
        raw = data.get('image_urls')
        urls: list[str] = []
        if isinstance(raw, str):
            import json
            try:
                raw = json.loads(raw)
            except (ValueError, TypeError):
                raw = [raw] if raw else []
        if isinstance(raw, list):
            for u in raw:
                if isinstance(u, str) and u and u not in urls:
                    urls.append(u)
        single = data.get('image_url') or ''
        if isinstance(single, str) and single and single not in urls:
            urls.insert(0, single)
        return urls

    @staticmethod
    def _serialize_post(p: ConsumerPost, liked_by_me: bool = False) -> dict:
        raw_tags = list(p.classroom_tags or [])
        image_urls = list(p.image_urls or [])
        if not image_urls and p.image_url:
            image_urls = [p.image_url]
        return {
            'uid':            str(p.uid),
            'consumer_uid':   str(p.consumer_uid),
            'author_name':    p.author_name or '',
            'author_avatar':  p.author_avatar or '',
            'author_type':    p.author_type or 'consumer',
            'space_uid':      str(p.space_uid) if p.space_uid else None,
            'content':        p.content or '',
            'emotion':        p.emotion or '',
            'image_url':      p.image_url or (image_urls[0] if image_urls else ''),
            'image_urls':     image_urls,
            'visibility':     p.visibility or 'public',
            'classroom_tags': [str(t) for t in raw_tags],
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

    def create_post(self, consumer_uid, author_name: str, author_avatar: str, data: dict,
                    author_type: str = 'consumer', space_uid=None) -> dict:
        raw_tags = data.get('classroom_tags') or data.get('classroom_tag') or []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        tag_uuids = []
        for t in raw_tags:
            if not t:
                continue
            try:
                tag_uuids.append(uuid.UUID(str(t)))
            except (ValueError, TypeError):
                continue

        image_urls = self._coerce_image_urls(data)
        image_url_first = image_urls[0] if image_urls else ''

        space_uuid = None
        if author_type == 'space' and space_uid:
            try:
                space_uuid = uuid.UUID(str(space_uid))
            except (ValueError, TypeError):
                space_uuid = None

        post = ConsumerPost.create(
            consumer_uid=uuid.UUID(str(consumer_uid)),
            author_name=author_name,
            author_avatar=author_avatar,
            author_type=author_type,
            space_uid=space_uuid,
            content=data.get('content', ''),
            emotion=data.get('emotion', ''),
            image_url=image_url_first,
            image_urls=image_urls,
            visibility=data.get('visibility', 'public'),
            classroom_tags=tag_uuids,
            created_at=datetime.utcnow(),
        )
        try:
            ProfileService().increment_posts(consumer_uid, 1)
        except Exception:
            pass
        return self._serialize_post(post)

    def upload_post_images(self, files, owner_id: str) -> tuple[list[str], list[dict]]:
        """Upload multiple files to R2 under posts/{owner_id}/. Returns (urls, errors)."""
        urls: list[str] = []
        errors: list[dict] = []
        for f in files:
            try:
                ext = os.path.splitext(f.name)[1] or '.jpg'
                object_key = f"posts/{owner_id}/{uuid.uuid4()}{ext}"
                result = storage_service.upload_fileobj(f, object_key, is_public=True)
                if result.get('success'):
                    urls.append(result.get('url', ''))
                else:
                    errors.append({'name': f.name, 'error': result.get('message', 'Upload failed')})
            except Exception as e:
                errors.append({'name': getattr(f, 'name', ''), 'error': str(e)})
        return urls, errors

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
        try:
            ProfileService().increment_posts(consumer_uid, -1)
        except Exception:
            pass
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
