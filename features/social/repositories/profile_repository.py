import uuid
from features.social.models.user_profile import UserProfile


class ProfileRepository:
    def get_by_owner(self, owner_id):
        if isinstance(owner_id, str):
            owner_id = uuid.UUID(owner_id)
        rows = list(UserProfile.objects.filter(bucket=0, owner_id=owner_id).limit(1))
        return rows[0] if rows else None

    def get_or_create(self, owner_id, owner_type: str) -> UserProfile:
        if isinstance(owner_id, str):
            owner_id = uuid.UUID(owner_id)
        existing = self.get_by_owner(owner_id)
        if existing:
            return existing
        return UserProfile.create(
            bucket=0,
            owner_id=owner_id,
            owner_type=owner_type,
        )

    def update(self, profile: UserProfile, data: dict) -> UserProfile:
        from datetime import datetime
        allowed = {
            'avatar_url', 'cover_url', 'bio', 'major', 'department',
            'skills', 'github', 'linkedin', 'website',
        }
        kwargs = {k: v for k, v in data.items() if k in allowed}
        kwargs['updated_at'] = datetime.utcnow()
        profile.update(**kwargs)
        return profile

    def increment_posts(self, owner_id, delta: int = 1):
        p = self.get_by_owner(owner_id)
        if not p:
            return
        new_count = max(0, int(p.posts_count or 0) + delta)
        p.update(posts_count=new_count)

    def _safe_increment(self, owner_id, field: str, delta: int) -> None:
        p = self.get_by_owner(owner_id)
        if not p:
            return
        current = int(getattr(p, field, 0) or 0)
        new_count = max(0, current + delta)
        p.update(**{field: new_count})

    def increment_followers(self, owner_id, delta: int = 1):
        self._safe_increment(owner_id, 'followers_count', delta)

    def increment_following(self, owner_id, delta: int = 1):
        self._safe_increment(owner_id, 'following_count', delta)
