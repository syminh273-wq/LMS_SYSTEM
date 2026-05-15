import string
import random
from features.sharing.repositories import LinkRepository

class LinkService:
    def __init__(self):
        self.repository = LinkRepository()

    def all(self):
        return self.repository.all()

    def find(self, uid):
        return self.repository.find(uid)

    def get_by_code(self, code):
        return self.repository.get_by_code(code)

    def generate_code(self, length=6):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def create_link(self, data: dict):
        if 'code' not in data or not data['code']:
            data['code'] = self.generate_code()
        return self.repository.create(**data)

    def update(self, instance, **kwargs):
        return self.repository.update(instance, **kwargs)

    def delete(self, instance):
        return self.repository.delete(instance)

    def get_resolve_url(self, code):
        """
        Return the public URL that the frontend will use to resolve the link.
        The frontend will use this URL to generate its own QR code.
        """
        # In production, this should be your actual domain
        return f"https://lms.example.com/resolve/{code}"
