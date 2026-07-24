import logging
from urllib.parse import parse_qs

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_str):
    try:
        from rest_framework_simplejwt.tokens import UntypedToken
        validated = UntypedToken(token_str)
        user_id = validated['user_id']
        user_type = validated.get('user_type')
        if user_type == 'space':
            from features.account.space.models.space import Space
            return Space.objects.filter(uid=user_id).allow_filtering().first()
        if user_type == 'consumer':
            from features.account.consumer.models.consumer import Consumer
            return Consumer.objects.filter(uid=user_id).allow_filtering().first()
        from features.account.space.models.space import Space as _Space
        from features.account.consumer.models.consumer import Consumer as _Consumer
        space_user = _Space.objects.filter(uid=user_id).allow_filtering().first()
        if space_user:
            return space_user
        return _Consumer.objects.filter(uid=user_id).allow_filtering().first()
    except Exception as e:
        logger.warning(f"WS JWT auth failed: {e}")
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', [])
        if token_list:
            scope['user'] = await get_user_from_token(token_list[0])
        else:
            scope['user'] = AnonymousUser()
        return await super().__call__(scope, receive, send)
