from urllib.parse import urlencode

import requests as http_requests
from django.conf import settings
from django.shortcuts import redirect
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models.social_account import SocialAccount
from features.account.space.repositories.space_repository import Repository as SpaceRepository


class GoogleSpaceOAuthLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_SPACE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
        }
        return redirect(f'{settings.GOOGLE_AUTH_URL}?{urlencode(params)}')


class GoogleSpaceOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        frontend_url = settings.FRONTEND_SPACE_URL
        code = request.GET.get('code')
        error_param = request.GET.get('error')

        if error_param:
            # 'interaction_required' / 'login_required' thường đến từ prompt=none khi session Google đã hết
            safe_error = 'google_auth_failed' if error_param in ('access_denied', 'interaction_required') else 'google_auth_failed'
            return redirect(f'{frontend_url}/space/login?error={safe_error}')

        if not code:
            return redirect(f'{frontend_url}/space/login?error=google_auth_failed')

        token_resp = http_requests.post(settings.GOOGLE_TOKEN_URL, data={
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.GOOGLE_SPACE_REDIRECT_URI,
        })

        if not token_resp.ok:
            return redirect(f'{frontend_url}/space/login?error=google_token_failed')

        raw_id_token = token_resp.json().get('id_token')

        try:
            idinfo = google_id_token.verify_oauth2_token(
                raw_id_token, GoogleRequest(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return redirect(f'{frontend_url}/space/login?error=google_token_invalid')

        google_sub = idinfo['sub']
        email = idinfo.get('email', '')
        full_name = idinfo.get('name', '')
        logo_url = idinfo.get('picture', '')

        repo = SpaceRepository()

        social = SocialAccount.objects.filter(
            provider='google', provider_id=google_sub
        ).first()

        if social and social.user_type == 'space':
            space = repo.filter(uid=social.user_uid, is_deleted=False).first()
        else:
            space = repo.filter(email=email, is_deleted=False).first()
            if not space:
                from django.contrib.auth.hashers import make_password
                space = repo.create(
                    email=email,
                    full_name=full_name,
                    name=full_name,
                    logo_url=logo_url,
                    password=make_password(None),
                    is_verified=True,
                    is_active=True,
                )

            if not social:
                SocialAccount.objects.create(
                    provider='google',
                    provider_id=google_sub,
                    user_uid=space.uid,
                    user_type='space',
                    email=email,
                )

        if not space or not space.is_active:
            return redirect(f'{frontend_url}/space/login?error=account_disabled')

        refresh = RefreshToken.for_user(space)
        refresh['user_type'] = 'space'
        refresh.access_token['user_type'] = 'space'

        return redirect(
            f'{frontend_url}/space/auth/callback'
            f'?access={str(refresh.access_token)}'
            f'&refresh={str(refresh)}'
        )
