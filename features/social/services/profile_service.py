from features.account.consumer.models import Consumer
from features.account.space.models import Space
from features.social.models.user_profile import UserProfile
from features.social.repositories.profile_repository import ProfileRepository


def _detect_owner_type(user) -> str:
    if isinstance(user, Space):
        return 'space'
    return 'consumer'


def _owner_id(user):
    return user.uid


class ProfileService:
    MAX_SKILLS = 20
    MAX_BIO = 500

    def __init__(self):
        self.repo = ProfileRepository()

    @staticmethod
    def serialize(p: UserProfile) -> dict:
        return {
            'owner_id': str(p.owner_id),
            'owner_type': p.owner_type,
            'avatar_url': p.avatar_url or '',
            'cover_url': p.cover_url or '',
            'bio': p.bio or '',
            'major': p.major or '',
            'department': p.department or '',
            'skills': list(p.skills or []),
            'github': p.github or '',
            'linkedin': p.linkedin or '',
            'website': p.website or '',
            'posts_count': int(p.posts_count or 0),
            'followers_count': int(p.followers_count or 0),
            'following_count': int(p.following_count or 0),
            'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        }

    def get_or_create_for_user(self, user):
        owner_type = _detect_owner_type(user)
        return self.repo.get_or_create(_owner_id(user), owner_type)

    def get_mine(self, user) -> dict:
        return self.serialize(self.get_or_create_for_user(user))

    def get_public(self, owner_id) -> dict | None:
        p = self.repo.get_by_owner(owner_id)
        return self.serialize(p) if p else None

    def update_mine(self, user, data: dict) -> dict:
        profile = self.get_or_create_for_user(user)

        clean = {}
        if 'bio' in data:
            clean['bio'] = (data.get('bio') or '')[:self.MAX_BIO]
        if 'major' in data:
            clean['major'] = (data.get('major') or '')[:120]
        if 'department' in data:
            clean['department'] = (data.get('department') or '')[:120]
        if 'github' in data:
            clean['github'] = (data.get('github') or '')[:200]
        if 'linkedin' in data:
            clean['linkedin'] = (data.get('linkedin') or '')[:200]
        if 'website' in data:
            clean['website'] = (data.get('website') or '')[:200]
        if 'avatar_url' in data:
            clean['avatar_url'] = (data.get('avatar_url') or '')[:500]
        if 'cover_url' in data:
            clean['cover_url'] = (data.get('cover_url') or '')[:500]
        if 'skills' in data:
            raw = data.get('skills') or []
            if not isinstance(raw, list):
                raw = []
            clean['skills'] = [str(s).strip()[:40] for s in raw if str(s).strip()][:self.MAX_SKILLS]

        updated = self.repo.update(profile, clean)
        return self.serialize(updated)

    def increment_posts(self, owner_id, delta: int = 1):
        self.repo.increment_posts(owner_id, delta)

    def increment_followers(self, owner_id, delta: int = 1):
        self.repo.increment_followers(owner_id, delta)

    def increment_following(self, owner_id, delta: int = 1):
        self.repo.increment_following(owner_id, delta)
