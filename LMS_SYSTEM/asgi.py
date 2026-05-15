"""
ASGI config for LMS_SYSTEM project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from core.ws.middleware.jwt_auth_middleware import JWTAuthMiddleware
import core.ws.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            core.ws.routing.websocket_urlpatterns
        )
    ),
})
