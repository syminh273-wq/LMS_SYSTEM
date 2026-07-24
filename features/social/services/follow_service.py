import uuid
from datetime import datetime
from core.storages.storage_service import storage_service
from features.social.models import UserFollow
from features.social.services.profile_service import ProfileService


def _resolve_avatar(value: str) -> str:
    if not value:
        return ''
    return storage_service.get_public_url(value)


class FollowService:

    @staticmethod
    def _serialize_follow(f: UserFollow, mode='following') -> dict:
        if mode == 'following':
            return {
                'consumer_uid': str(f.followed_uid),
                'name': f.followed_name,
                'avatar': _resolve_avatar(f.followed_avatar or ''),
                'created_at': f.created_at.isoformat() if f.created_at else None
            }
        else:
            return {
                'consumer_uid': str(f.follower_uid),
                'name': f.follower_name,
                'avatar': _resolve_avatar(f.follower_avatar or ''),
                'created_at': f.created_at.isoformat() if f.created_at else None
            }

    def follow_user(self, follower_uid, followed_uid, follower_data: dict, followed_data: dict) -> bool:
        f_uid = uuid.UUID(str(follower_uid))
        t_uid = uuid.UUID(str(followed_uid))

        if f_uid == t_uid:
            return False

        existing = list(UserFollow.objects.filter(follower_uid=f_uid, followed_uid=t_uid).limit(1))
        if existing:
            return True # already following

        UserFollow.create(
            follower_uid=f_uid,
            followed_uid=t_uid,
            follower_name=follower_data.get('name', ''),
            follower_avatar=follower_data.get('avatar', ''),
            followed_name=followed_data.get('name', ''),
            followed_avatar=followed_data.get('avatar', ''),
            created_at=datetime.utcnow()
        )

        try:
            svc = ProfileService()
            svc.increment_followers(t_uid, 1)
            svc.increment_following(f_uid, 1)
        except Exception:
            pass

        return True

    def unfollow_user(self, follower_uid, followed_uid) -> bool:
        f_uid = uuid.UUID(str(follower_uid))
        t_uid = uuid.UUID(str(followed_uid))

        existing = list(UserFollow.objects.filter(follower_uid=f_uid, followed_uid=t_uid).limit(1))
        if existing:
            existing[0].delete()
            try:
                svc = ProfileService()
                svc.increment_followers(t_uid, -1)
                svc.increment_following(f_uid, -1)
            except Exception:
                pass
            return True
        return False

    def is_following(self, follower_uid, followed_uid) -> bool:
        if not follower_uid or not followed_uid:
            return False
        f_uid = uuid.UUID(str(follower_uid))
        t_uid = uuid.UUID(str(followed_uid))
        return UserFollow.objects.filter(follower_uid=f_uid, followed_uid=t_uid).count() > 0

    def get_following(self, follower_uid, limit: int = 50) -> list[dict]:
        f_uid = uuid.UUID(str(follower_uid))
        follows = list(UserFollow.objects.filter(follower_uid=f_uid).limit(limit))
        return [self._serialize_follow(f, 'following') for f in follows]

    def get_followers(self, followed_uid, limit: int = 50) -> list[dict]:
        t_uid = uuid.UUID(str(followed_uid))
        # Note: Index on followed_uid allows this query
        follows = list(UserFollow.objects.filter(followed_uid=t_uid).limit(limit))
        return [self._serialize_follow(f, 'followers') for f in follows]
