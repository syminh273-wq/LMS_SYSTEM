from urllib.parse import urlencode

import requests as http_requests
from django.conf import settings
from django.shortcuts import redirect
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models.social_account import SocialAccount
from features.account.consumer.repositories.consumer_repository import ConsumerRepository

class GoogleConsumerOAuthLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_CONSUMER_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
        }
        return redirect(f'{settings.GOOGLE_AUTH_URL}?{urlencode(params)}')


class GoogleConsumerOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        frontend_url = settings.FRONTEND_CONSUMER_URL
        code = request.GET.get('code')

        if request.GET.get('error') or not code:
            return redirect(f'{frontend_url}/consumer/login?error=google_auth_failed')

        # Exchange code for tokens
        token_resp = http_requests.post(settings.GOOGLE_TOKEN_URL, data={
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.GOOGLE_CONSUMER_REDIRECT_URI,
        })

        if not token_resp.ok:
            return redirect(f'{frontend_url}/consumer/login?error=google_token_failed')

        raw_id_token = token_resp.json().get('id_token')

        try:
            idinfo = google_id_token.verify_oauth2_token(
                raw_id_token, GoogleRequest(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return redirect(f'{frontend_url}/consumer/login?error=google_token_invalid')

        google_sub = idinfo['sub']
        email = idinfo.get('email', '')
        full_name = idinfo.get('name', '')
        avatar_url = idinfo.get('picture', '')

        repo = ConsumerRepository()

        # Tìm SocialAccount đã link
        social = SocialAccount.objects.filter(
            provider='google', provider_id=google_sub
        ).first()

        if social:
            consumer = repo.filter(uid=social.user_uid, is_deleted=False).first()
        else:
            # Tìm Consumer theo email
            consumer = repo.filter(email=email, is_deleted=False).first()
            if consumer:
                # Link google account vào consumer hiện tại
                SocialAccount.objects.create(
                    provider='google',
                    provider_id=google_sub,
                    user_uid=consumer.uid,
                    user_type='consumer',
                    email=email,
                )
            else:
                from django.contrib.auth.hashers import make_password
                consumer = repo.create(
                    email=email,
                    username=email,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    password=make_password(None),
                    is_verified=True,
                    is_active=True,
                )
                SocialAccount.objects.create(
                    provider='google',
                    provider_id=google_sub,
                    user_uid=consumer.uid,
                    user_type='consumer',
                    email=email,
                )

        if not consumer or not consumer.is_active:
            return redirect(f'{frontend_url}/consumer/login?error=account_disabled')

        refresh = RefreshToken.for_user(consumer)
        refresh['user_type'] = 'consumer'
        refresh.access_token['user_type'] = 'consumer'

        return redirect(
            f'{frontend_url}/consumer/auth/callback'
            f'?access={str(refresh.access_token)}'
            f'&refresh={str(refresh)}'
        )
