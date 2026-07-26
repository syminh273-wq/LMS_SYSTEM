import uuid
from datetime import datetime
from core.storages.storage_service import storage_service
from features.social.models import SocialFollow
from features.social.services.profile_service import ProfileService


def _resolve_avatar(value: str) -> str:
    if not value:
        return ''
    return storage_service.get_public_url(value)


class FollowService:

    @staticmethod
    def _serialize_follow(f: SocialFollow, mode='following') -> dict:
        if mode == 'following':
            return {
                'owner_id': str(f.followed_id),
                'owner_type': f.followed_type or 'consumer',
                'name': f.followed_name,
                'avatar': _resolve_avatar(f.followed_avatar or ''),
                'created_at': f.created_at.isoformat() if f.created_at else None
            }
        else:
            return {
                'owner_id': str(f.follower_id),
                'owner_type': f.follower_type or 'consumer',
                'name': f.follower_name,
                'avatar': _resolve_avatar(f.follower_avatar or ''),
                'created_at': f.created_at.isoformat() if f.created_at else None
            }

    def follow_user(self, follower_id, followed_id, follower_data: dict, followed_data: dict) -> bool:
        f_id = uuid.UUID(str(follower_id))
        t_id = uuid.UUID(str(followed_id))

        if f_id == t_id:
            return False

        existing = list(SocialFollow.objects.filter(follower_id=f_id, followed_id=t_id).limit(1))
        if existing:
            return True

        SocialFollow.create(
            follower_id=f_id,
            followed_id=t_id,
            follower_type=follower_data.get('type', 'consumer'),
            followed_type=followed_data.get('type', 'consumer'),
            follower_name=follower_data.get('name', ''),
            follower_avatar=follower_data.get('avatar', ''),
            followed_name=followed_data.get('name', ''),
            followed_avatar=followed_data.get('avatar', ''),
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

        existing = list(SocialFollow.objects.filter(follower_id=f_id, followed_id=t_id).limit(1))
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
        return SocialFollow.objects.filter(follower_id=f_id, followed_id=t_id).count() > 0

    def get_following(self, follower_id, limit: int = 50) -> list[dict]:
        f_id = uuid.UUID(str(follower_id))
        follows = list(SocialFollow.objects.filter(follower_id=f_id).limit(limit))
        return [self._serialize_follow(f, 'following') for f in follows]

    def get_followers(self, followed_id, limit: int = 50) -> list[dict]:
        t_id = uuid.UUID(str(followed_id))
        follows = list(SocialFollow.objects.filter(followed_id=t_id).limit(limit))
        return [self._serialize_follow(f, 'followers') for f in follows]
