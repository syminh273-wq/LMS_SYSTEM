from rest_framework import exceptions
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


class AccountTokenRefreshSerializer(TokenRefreshSerializer):
    default_user_type = 'consumer'
    token_class = RefreshToken

    default_error_messages = {
        'no_active_account': 'No active account found for the given token.',
    }

    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])

        try:
            refresh_payload = refresh.payload
        except Exception:
            raise exceptions.InvalidToken('Token is invalid or expired')

        user_id = refresh_payload.get(api_settings.USER_ID_CLAIM)
        user_type = refresh_payload.get('user_type', self.default_user_type)
        if not user_id:
            raise exceptions.InvalidToken('Token contained no recognizable user identification')

        if user_type == 'space':
            from features.account.space.models.space import Space
            user = Space.objects.filter(uid=user_id).allow_filtering().first()
        elif user_type == 'consumer':
            from features.account.consumer.models.consumer import Consumer
            user = Consumer.objects.filter(uid=user_id).allow_filtering().first()
        else:
            raise exceptions.InvalidToken(f'Unknown user_type: {user_type}')

        if not user:
            raise exceptions.InvalidToken('User not found', code='user_not_found')
        if not getattr(user, 'is_active', True):
            raise exceptions.InvalidToken('User is inactive', code='user_inactive')

        data = {'access': str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            refresh.outstand()
            data['refresh'] = str(refresh)

        return data
