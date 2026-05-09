from features.account.space.repositories import Repository


class Service:
    def __init__(self):
        self.repository = Repository()

    def all(self):
        return self.repository.all()

    def find(self, uid):
        return self.repository.find(uid)

    def get_by_slug(self, slug: str):
        return self.repository.get_by_slug(slug)

    def get_spaces_of_owner(self, owner_uid):
        return self.repository.get_by_owner(owner_uid)

    def get_active_spaces(self):
        return self.repository.get_active()

    def create_space(self, owner_uid, data: dict):
        return self.repository.create(owner_uid=owner_uid, **data)

    def update(self, instance, **kwargs):
        return self.repository.update(instance, **kwargs)

    def delete(self, instance):
        return self.repository.delete(instance)

    def deactivate(self, instance):
        return self.repository.update(instance, is_active=False)
