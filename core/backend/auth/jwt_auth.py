from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions

class CassandraJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            user_type = validated_token.get('user_type', 'consumer')

            if user_type == 'space':
                from features.account.space.models.space import Space
                user = Space.objects.filter(uid=user_id).allow_filtering().first()
            else:
                from features.account.consumer.models.consumer import Consumer
                user = Consumer.objects.filter(uid=user_id).allow_filtering().first()

            if not user:
                raise exceptions.AuthenticationFailed('User not found', code='user_not_found')
            
            if not user.is_active:
                raise exceptions.AuthenticationFailed('User is inactive', code='user_inactive')
                
            return user
        except KeyError:
            raise exceptions.AuthenticationFailed('Token contained no recognizable user identification')
        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e))
