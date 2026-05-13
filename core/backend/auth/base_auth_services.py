from django.contrib.auth.hashers import make_password, check_password
from core.services.base_service import BaseService


class BaseAuthService(BaseService):
    """
    Base service for authentication-related actions (register, login, etc.).
    Child classes must define `self.repository`.
    """

    def register(self, data: dict):
        """
        Common registration logic: hash the password before creating the record.
        """
        password = data.pop('password', None)
        if password:
            data['password'] = make_password(password)

        if 'email' in data and not data.get('username'):
            data['username'] = data['email']

        return self.create(**data)

    def authenticate(self, username, password, login_field="email"):
        """
        Common authentication logic: 
        Find an active user by a specific field (default 'username') and verify the password.
        """
        kwargs = {
            login_field: username,
            "is_active": True,
        }
        
        # Check if the model uses soft delete
        if hasattr(self.repository.model, 'is_deleted'):
            kwargs['is_deleted'] = False

        user = self.repository.filter(**kwargs).first()
        
        if user and check_password(password, getattr(user, 'password', '')):
            return user
        return None
