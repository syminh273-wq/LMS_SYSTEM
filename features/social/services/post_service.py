import os
import uuid
from datetime import datetime

from core.storages.storage_service import storage_service
from features.social.models import SocialPost, SocialPostLike, SocialPostComment, SocialProfile
from features.social.services.follow_service import FollowService
from features.social.services.profile_service import ProfileService


class PostService:

    @staticmethod
    def _coerce_image_urls(data: dict) -> list[str]:
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
    def _resolve_avatar_url(value: str) -> str:
        if not value:
            return ''
        return storage_service.get_public_url(value)

    @staticmethod
    def _profile_avatar_map(owner_ids: list) -> dict:
        if not owner_ids:
            return {}
        result: dict[str, str] = {}
        for raw in owner_ids:
            try:
                owner_uuid = uuid.UUID(str(raw))
            except (ValueError, TypeError):
                continue
            try:
                rows = list(SocialProfile.objects.filter(owner_id=owner_uuid).limit(1))
            except Exception:
                continue
            if rows and rows[0].avatar_url:
                result[str(owner_uuid)] = rows[0].avatar_url
        return result

    @staticmethod
    def _backfill_avatar(stored: str, owner_id, profile_avatars: dict) -> str:
        value = (stored or '').strip()
        if not value and owner_id is not None:
            value = (profile_avatars.get(str(owner_id)) or '').strip()
        return PostService._resolve_avatar_url(value)

    @staticmethod
    def _serialize_post(p: SocialPost, liked_by_me: bool = False,
                        profile_avatars: dict | None = None) -> dict:
        raw_tags = list(p.classroom_tags or [])
        image_urls = list(p.image_urls or [])
        if not image_urls and p.image_url:
            image_urls = [p.image_url]
        profile_avatars = profile_avatars or {}
        author_avatar = PostService._backfill_avatar(
            p.owner_avatar, p.owner_id, profile_avatars
        )
        return {
            'uid':            str(p.uid),
            'owner_id':       str(p.owner_id),
            'owner_type':     p.owner_type or 'consumer',
            'author_name':    p.owner_name or '',
            'author_avatar':  author_avatar,
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
    def _serialize_comment(c: SocialPostComment, profile_avatars: dict | None = None) -> dict:
        profile_avatars = profile_avatars or {}
        author_avatar = PostService._backfill_avatar(
            c.owner_avatar, c.owner_id, profile_avatars
        )
        return {
            'uid':           str(c.uid),
            'post_uid':      str(c.post_uid),
            'owner_id':      str(c.owner_id),
            'owner_type':    c.owner_type or 'consumer',
            'author_name':   c.owner_name or '',
            'author_avatar': author_avatar,
            'content':       c.content or '',
            'created_at':    c.created_at.isoformat() if c.created_at else None,
        }

    def create_post(self, owner_id, owner_name: str, owner_avatar: str, data: dict,
                    owner_type: str = 'consumer', space_uid=None) -> dict:
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
        if owner_type == 'space' and space_uid:
            try:
                space_uuid = uuid.UUID(str(space_uid))
            except (ValueError, TypeError):
                space_uuid = None

        post = SocialPost.create(
            owner_id=uuid.UUID(str(owner_id)),
            owner_type=owner_type,
            owner_name=owner_name,
            owner_avatar=owner_avatar,
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
            ProfileService().increment_posts(owner_id, 1)
        except Exception:
            pass
        return self._serialize_post(post)

    def upload_post_images(self, files, owner_id: str) -> tuple[list[str], list[dict]]:
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
        qs = SocialPost.objects.filter(is_deleted=False)
        if before:
            try:
                qs = qs.filter(created_at__lt=datetime.fromisoformat(before))
            except Exception:
                pass
        posts = list(qs.limit(limit * 2))
        posts = [p for p in posts if p.visibility == 'public'][:limit]

        liked_set = self._liked_set(requester_uid, [p.uid for p in posts])
        profile_avatars = self._profile_avatar_map([p.owner_id for p in posts])
        return [self._serialize_post(p, str(p.uid) in liked_set, profile_avatars) for p in posts]

    def get_following_feed(self, requester_uid, limit: int = 20) -> list[dict]:
        following = FollowService().get_following(requester_uid, limit=200)
        followed_uids = [uuid.UUID(f['owner_id']) for f in following]

        if not followed_uids:
            return []

        qs = SocialPost.objects.filter(is_deleted=False).limit(limit * 5)
        posts_raw = list(qs)

        followed_set = {str(uid) for uid in followed_uids}
        posts = [p for p in posts_raw if str(p.owner_id) in followed_set][:limit]

        liked_set = self._liked_set(requester_uid, [p.uid for p in posts])
        profile_avatars = self._profile_avatar_map([p.owner_id for p in posts])
        return [self._serialize_post(p, str(p.uid) in liked_set, profile_avatars) for p in posts]

    def get_my_posts(self, owner_id, limit: int = 20, before: str | None = None) -> list[dict]:
        qs = SocialPost.objects.filter(owner_id=uuid.UUID(str(owner_id)), is_deleted=False)
        if before:
            try:
                qs = qs.filter(created_at__lt=datetime.fromisoformat(before))
            except Exception:
                pass
        posts = list(qs.limit(limit))
        profile_avatars = self._profile_avatar_map([p.owner_id for p in posts])
        return [self._serialize_post(p, profile_avatars=profile_avatars) for p in posts]

    def get_user_posts(self, owner_id, requester_uid, limit: int = 20) -> list[dict]:
        is_owner = str(owner_id) == str(requester_uid)
        posts_raw = list(
            SocialPost.objects.filter(owner_id=uuid.UUID(str(owner_id)), is_deleted=False).limit(limit * 2)
        )
        if is_owner:
            posts = posts_raw[:limit]
        else:
            posts = [p for p in posts_raw if p.visibility == 'public'][:limit]

        liked_set = self._liked_set(requester_uid, [p.uid for p in posts])
        profile_avatars = self._profile_avatar_map([p.owner_id for p in posts])
        return [self._serialize_post(p, str(p.uid) in liked_set, profile_avatars) for p in posts]

    def get_post(self, post_uid: str) -> SocialPost | None:
        try:
            results = list(SocialPost.objects.filter(uid=uuid.UUID(post_uid)).limit(1))
            return results[0] if results else None
        except Exception:
            return None

    def delete_post(self, post_uid: str, owner_id) -> bool:
        post = self.get_post(post_uid)
        if not post or str(post.owner_id) != str(owner_id):
            return False
        post.update(is_deleted=True)
        try:
            ProfileService().increment_posts(owner_id, -1)
        except Exception:
            pass
        return True

    def toggle_like(self, post_uid: str, owner_id) -> dict:
        p_uid = uuid.UUID(post_uid)
        o_uid = uuid.UUID(str(owner_id))
        existing = list(SocialPostLike.objects.filter(post_uid=p_uid, owner_id=o_uid).limit(1))

        post = self.get_post(post_uid)
        if not post:
            raise ValueError('Post not found')

        if existing:
            existing[0].delete()
            new_count = max(0, int(post.likes_count or 0) - 1)
            post.update(likes_count=new_count)
            return {'liked': False, 'likes_count': new_count}
        else:
            SocialPostLike.create(post_uid=p_uid, owner_id=o_uid)
            new_count = int(post.likes_count or 0) + 1
            post.update(likes_count=new_count)
            return {'liked': True, 'likes_count': new_count}

    def _liked_set(self, owner_id, post_uids: list) -> set:
        if not post_uids or not owner_id:
            return set()
        result = set()
        o_uid = uuid.UUID(str(owner_id))
        for p_uid in post_uids:
            rows = list(SocialPostLike.objects.filter(post_uid=p_uid, owner_id=o_uid).limit(1))
            if rows:
                result.add(str(p_uid))
        return result

    def get_comments(self, post_uid: str, limit: int = 30) -> list[dict]:
        comments = list(
            SocialPostComment.objects.filter(post_uid=uuid.UUID(post_uid), is_deleted=False).limit(limit)
        )
        profile_avatars = self._profile_avatar_map([c.owner_id for c in comments])
        return [self._serialize_comment(c, profile_avatars) for c in comments]

    def add_comment(self, post_uid: str, owner_id, owner_name: str, owner_avatar: str, content: str,
                     owner_type: str = 'consumer') -> dict:
        p_uid = uuid.UUID(post_uid)
        comment = SocialPostComment.create(
            post_uid=p_uid,
            owner_id=uuid.UUID(str(owner_id)),
            owner_type=owner_type,
            owner_name=owner_name,
            owner_avatar=owner_avatar,
            content=content,
            created_at=datetime.utcnow(),
        )
        post = self.get_post(post_uid)
        if post:
            post.update(comments_count=int(post.comments_count or 0) + 1)
        return self._serialize_comment(comment)

    def delete_comment(self, post_uid: str, comment_uid: str, owner_id) -> bool:
        try:
            rows = list(
                SocialPostComment.objects.filter(post_uid=uuid.UUID(post_uid), uid=uuid.UUID(comment_uid)).limit(1)
            )
            if not rows:
                return False
            c = rows[0]
            if str(c.owner_id) != str(owner_id):
                return False
            c.update(is_deleted=True)
            post = self.get_post(post_uid)
            if post:
                post.update(comments_count=max(0, int(post.comments_count or 0) - 1))
            return True
        except Exception:
            return False
