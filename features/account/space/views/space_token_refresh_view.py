from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenViewBase

from core.backend.auth.refresh import AccountTokenRefreshSerializer


class SpaceAccountTokenRefreshView(TokenViewBase):
    serializer_class = type(
        'SpaceAccountTokenRefreshSerializer',
        (AccountTokenRefreshSerializer,),
        {'default_user_type': 'space'},
    )
    permission_classes = [AllowAny]
