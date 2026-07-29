from features.account.consumer.models import Consumer
from features.account.space.models import Space
from features.social.models.social_profile import SocialProfile
from features.social.repositories.profile_repository import ProfileRepository
from features.portfolio.services.portfolio_service import PortfolioService
from core.services.base_service import BaseService


def _detect_owner_type(user) -> str:
    if isinstance(user, Space):
        return 'space'
    return 'consumer'


def _owner_id(user):
    return user.uid


class ProfileService(BaseService):
    MAX_SKILLS = 20
    MAX_BIO = 500
    MAX_LINK = 200

    def __init__(self):
        self.repo = ProfileRepository()
        self.portfolio_service = PortfolioService()

    @staticmethod
    def serialize(p: SocialProfile, social_profile: dict | None = None) -> dict:
        social_profile = social_profile or {}
        return {
            'owner_id': str(p.owner_id),
            'owner_type': p.owner_type,
            'avatar_url': p.avatar_url or '',
            'cover_url': p.cover_url or '',
            'bio': social_profile.get('bio', '') or '',
            'major': social_profile.get('major', '') or '',
            'department': social_profile.get('department', '') or '',
            'skills': list(social_profile.get('skills') or []),
            'github': social_profile.get('github', '') or '',
            'linkedin': social_profile.get('linkedin', '') or '',
            'website': social_profile.get('website', '') or '',
            'posts_count': int(p.posts_count or 0),
            'followers_count': int(p.followers_count or 0),
            'following_count': int(p.following_count or 0),
            'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        }

    def get_or_create_for_user(self, user):
        owner_type = _detect_owner_type(user)
        return self.repo.get_or_create(_owner_id(user), owner_type)

    def get_mine(self, user) -> dict:
        profile = self.get_or_create_for_user(user)
        owner_type = _detect_owner_type(user)
        social = self.portfolio_service.get_social_profile(_owner_id(user), owner_type)
        return self.serialize(profile, social)

    def get_public(self, owner_id) -> dict | None:
        p = self.repo.get_by_owner(owner_id)
        if not p:
            return None
        social = self.portfolio_service.get_social_profile(owner_id, p.owner_type)
        return self.serialize(p, social)

    def update_mine(self, user, data: dict) -> dict:
        profile = self.get_or_create_for_user(user)
        owner_id = _owner_id(user)
        owner_type = _detect_owner_type(user)

        social_clean = {}
        if 'bio' in data:
            social_clean['bio'] = (data.get('bio') or '')[:self.MAX_BIO]
        if 'major' in data:
            social_clean['major'] = (data.get('major') or '')[:120]
        if 'department' in data:
            social_clean['department'] = (data.get('department') or '')[:120]
        if 'github' in data:
            social_clean['github'] = (data.get('github') or '')[:self.MAX_LINK]
        if 'linkedin' in data:
            social_clean['linkedin'] = (data.get('linkedin') or '')[:self.MAX_LINK]
        if 'website' in data:
            social_clean['website'] = (data.get('website') or '')[:self.MAX_LINK]
        if 'skills' in data:
            raw = data.get('skills') or []
            if not isinstance(raw, list):
                raw = []
            social_clean['skills'] = [
                str(s).strip()[:40] for s in raw if str(s).strip()
            ][:self.MAX_SKILLS]

        for key, value in social_clean.items():
            import json
            self.portfolio_service.repository.upsert(
                owner_id=owner_id,
                owner_type=owner_type,
                key=key,
                value=json.dumps(value, ensure_ascii=False),
                is_public=True,
            )

        identity_clean = {}
        if 'avatar_url' in data:
            identity_clean['avatar_url'] = (data.get('avatar_url') or '')[:500]
        if 'cover_url' in data:
            identity_clean['cover_url'] = (data.get('cover_url') or '')[:500]

        updated = self.repo.update(profile, identity_clean) if identity_clean else profile
        social = self.portfolio_service.get_social_profile(owner_id, owner_type)
        return self.serialize(updated, social)

    def increment_posts(self, owner_id, delta: int = 1):
        self.repo.increment_posts(owner_id, delta)

    def increment_followers(self, owner_id, delta: int = 1):
        self.repo.increment_followers(owner_id, delta)

    def increment_following(self, owner_id, delta: int = 1):
        self.repo.increment_following(owner_id, delta)
