import logging

from features.social.repositories.classroom_favorite_repository import ClassroomFavoriteRepository
from features.social.serializers.classroom_favorite_serializer import ClassroomFavoriteResponseSerializer

logger = logging.getLogger(__name__)


class ClassroomFavoriteService:
    def __init__(self):
        self.repo = ClassroomFavoriteRepository()

    def is_favorited(self, consumer_uid, classroom_uid):
        return self.repo.is_favorited(consumer_uid, classroom_uid)

    def favorite_count(self, classroom_uid):
        return self.repo.count_for_classroom(classroom_uid)

    def toggle(self, consumer_uid, classroom_uid):
        """Toggle favorite. Returns {is_favorited, favorite_count}."""
        existing = self.repo.get(consumer_uid, classroom_uid)
        if existing is not None:
            self.repo.remove(consumer_uid, classroom_uid)
            is_favorited = False
        else:
            self.repo.add(consumer_uid, classroom_uid)
            is_favorited = True
        return {
            'is_favorited': is_favorited,
            'favorite_count': self.repo.count_for_classroom(classroom_uid),
        }

    def favorite(self, consumer_uid, classroom_uid):
        """Idempotent add."""
        self.repo.add(consumer_uid, classroom_uid)
        return {
            'is_favorited': True,
            'favorite_count': self.repo.count_for_classroom(classroom_uid),
        }

    def unfavorite(self, consumer_uid, classroom_uid):
        """Idempotent remove."""
        self.repo.remove(consumer_uid, classroom_uid)
        return {
            'is_favorited': False,
            'favorite_count': self.repo.count_for_classroom(classroom_uid),
        }

    def list_for_consumer(self, consumer_uid):
        """List favorites joined with classroom payload."""
        from features.course.classroom.repositories import Repository as ClassroomRepository

        repo = ClassroomRepository()
        out = []
        for fav in self.repo.list_by_consumer(consumer_uid):
            try:
                classroom = repo.find(str(fav.classroom_uid))
            except Exception:
                continue
            if getattr(classroom, 'is_deleted', False):
                continue
            out.append({
                'classroom': classroom,
                'created_at': fav.created_at,
            })
        return out

    def serialize(self, favorites):
        return ClassroomFavoriteResponseSerializer(favorites, many=True).data
