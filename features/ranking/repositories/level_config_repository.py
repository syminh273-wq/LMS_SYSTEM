from core.repositories.base_repository import BaseRepository
from features.ranking.models.level_config import LevelConfig


class LevelConfigRepository(BaseRepository):
    model = LevelConfig

    def all_levels(self):
        return sorted(list(self.model.objects(bucket=0)), key=lambda r: r.level)

    def get(self, level):
        return self.model.objects(bucket=0, level=level).first()

    def upsert(self, level, required_xp, title='', color='blue'):
        existing = self.get(level)
        if existing:
            existing.required_xp = required_xp
            existing.title = title
            existing.color = color
            existing.save()
            return existing
        return self.model.create(bucket=0, level=level, required_xp=required_xp,
                                 title=title, color=color)
