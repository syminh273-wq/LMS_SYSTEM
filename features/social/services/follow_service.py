import uuid
from datetime import datetime
from features.account.consumer.models import Consumer
from features.account.space.models import Space
from features.social.models import SocialFollow
from features.social.services.profile_service import ProfileService


def _resolve_avatar(value: str) -> str:
    if not value:
        return ''
    from core.storages.storage_service import storage_service
    return storage_service.get_public_url(value)


def _lookup_identity(owner_id, owner_type: str) -> dict:
    if isinstance(owner_id, str):
        owner_id = uuid.UUID(owner_id)
    user = None
    if owner_type == 'space':
        try:
            user = Space.objects.filter(uid=owner_id).first()
        except Exception:
            user = None
    else:
        try:
            user = Consumer.objects.filter(uid=owner_id).first()
        except Exception:
            user = None

    if user:
        return {
            'name': getattr(user, 'full_name', '') or getattr(user, 'name', '') or '',
            'avatar': getattr(user, 'avatar_url', '') or '',
        }
    return {'name': '', 'avatar': ''}


class FollowService:

    @staticmethod
    def _serialize_follow(f: SocialFollow, mode='following') -> dict:
        if mode == 'following':
            owner_id = f.followed_id
            owner_type = f.followed_type or 'consumer'
        else:
            owner_id = f.uid
            owner_type = f.follower_type or 'consumer'

        identity = _lookup_identity(owner_id, owner_type)
        return {
            'owner_id': str(owner_id),
            'owner_type': owner_type,
            'name': identity['name'],
            'avatar': _resolve_avatar(identity['avatar']),
            'created_at': f.created_at.isoformat() if f.created_at else None
        }

    def follow_user(self, follower_id, followed_id, follower_data: dict, followed_data: dict) -> bool:
        f_id = uuid.UUID(str(follower_id))
        t_id = uuid.UUID(str(followed_id))

        if f_id == t_id:
            return False

        existing = list(SocialFollow.objects.filter(uid=f_id, followed_id=t_id).limit(1))
        if existing:
            return True

        SocialFollow.create(
            uid=f_id,
            followed_id=t_id,
            follower_type=follower_data.get('type', 'consumer'),
            followed_type=followed_data.get('type', 'consumer'),
            created_at=datetime.utcnow()
        )

        try:
            svc = ProfileService()
            svc.increment_followers(t_id, 1)
            svc.increment_following(f_id, 1)
        except Exception:
            pass

        return True

    def unfollow_user(self, follower_id, followed_id) -> bool:
        f_id = uuid.UUID(str(follower_id))
        t_id = uuid.UUID(str(followed_id))

        existing = list(SocialFollow.objects.filter(uid=f_id, followed_id=t_id).limit(1))
        if existing:
            existing[0].delete()
            try:
                svc = ProfileService()
                svc.increment_followers(t_id, -1)
                svc.increment_following(f_id, -1)
            except Exception:
                pass
            return True
        return False

    def is_following(self, follower_id, followed_id) -> bool:
        if not follower_id or not followed_id:
            return False
        f_id = uuid.UUID(str(follower_id))
        t_id = uuid.UUID(str(followed_id))
        return SocialFollow.objects.filter(uid=f_id, followed_id=t_id).count() > 0

    def get_following(self, follower_id, limit: int = 50) -> list[dict]:
        f_id = uuid.UUID(str(follower_id))
        follows = list(SocialFollow.objects.filter(uid=f_id).limit(limit))
        return [self._serialize_follow(f, 'following') for f in follows]

    def get_followers(self, followed_id, limit: int = 50) -> list[dict]:
        t_id = uuid.UUID(str(followed_id))
        follows = list(SocialFollow.objects.filter(followed_id=t_id).limit(limit))
        return [self._serialize_follow(f, 'followers') for f in follows]
