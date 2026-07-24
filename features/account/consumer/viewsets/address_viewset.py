"""
Address API — 1 user : 1 address.

All endpoints are bound to the currently authenticated user (Consumer or
Space), resolved from the JWT `user_id` + `user_type` claims.

    GET    /api/v1/account/addresses/me/   → 200 with address | 200 with []
    PUT    /api/v1/account/addresses/me/   → create or replace (200)
    PATCH  /api/v1/account/addresses/me/   → partial update (200)
    DELETE /api/v1/account/addresses/me/   → soft delete (204)
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from features.account.consumer.services import AddressService


def _owner_id_and_type(request):
    """Resolve owner_id (UUID) and owner_type ('consumer' | 'space') from JWT."""
    user = request.user
    owner_id = getattr(user, 'uid', None)
    if owner_id is None:
        return None, None
    # jwt_auth.py adds the `user_type` claim to validated_token.
    # DRF SimpleJWT stores the raw token on request.auth.
    user_type = 'consumer'
    token = getattr(request, 'auth', None)
    if token is not None:
        try:
            user_type = token.get('user_type', 'consumer') or 'consumer'
        except Exception:
            user_type = 'consumer'
    return owner_id, user_type


class MyAddressView(APIView):
    """Single-address endpoint, scoped to the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        owner_id, owner_type = _owner_id_and_type(request)
        if not owner_id:
            return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        data = AddressService().get_for_owner(owner_id, owner_type)
        if data is None:
            return Response([], status=status.HTTP_200_OK)
        return Response(data)

    def put(self, request):
        return self._write(request, partial=False)

    def patch(self, request):
        return self._write(request, partial=True)

    def delete(self, request):
        owner_id, owner_type = _owner_id_and_type(request)
        if not owner_id:
            return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        ok = AddressService().soft_delete_for_owner(owner_id, owner_type)
        if not ok:
            return Response({'detail': 'Chưa có địa chỉ để xoá.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _write(self, request, partial: bool):
        owner_id, owner_type = _owner_id_and_type(request)
        if not owner_id:
            return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        data = AddressService().upsert_for_owner(owner_id, owner_type, request.data or {})
        return Response(data, status=status.HTTP_200_OK)
