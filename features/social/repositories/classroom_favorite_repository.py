from core.repositories.base_repository import BaseRepository
from features.social.models.classroom_favorite import ClassroomFavorite


class ClassroomFavoriteRepository(BaseRepository):
    model = ClassroomFavorite

    def list_by_consumer(self, consumer_uid):
        """All favorites of a consumer (single partition scan)."""
        return list(self.model.objects.filter(consumer_uid=consumer_uid))

    def get(self, consumer_uid, classroom_uid):
        return self.model.objects.filter(
            consumer_uid=consumer_uid,
            classroom_uid=classroom_uid,
        ).first()

    def is_favorited(self, consumer_uid, classroom_uid):
        return self.get(consumer_uid, classroom_uid) is not None

    def add(self, consumer_uid, classroom_uid):
        existing = self.get(consumer_uid, classroom_uid)
        if existing is not None:
            return existing
        return self.model.create(
            consumer_uid=consumer_uid,
            classroom_uid=classroom_uid,
        )

    def remove(self, consumer_uid, classroom_uid):
        existing = self.get(consumer_uid, classroom_uid)
        if existing is None:
            return False
        existing.delete()
        return True

    def count_for_classroom(self, classroom_uid):
        """Best-effort count. Cassandra has no `count(*) by non-partition`; iterate."""
        from features.social.models import ClassroomFavorite as CF
        rows = CF.objects.filter(classroom_uid=classroom_uid)
        return sum(1 for _ in rows)
